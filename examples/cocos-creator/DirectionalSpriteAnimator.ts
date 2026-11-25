/**
 * Cocos Creator 3.x — plays animations exported by AI Game Art Studio.
 *
 * Inputs (from an export folder's `cocos/` directory):
 *   - <name>.plist + <name>.png  → import into assets/; Creator creates a SpriteAtlas.
 *   - <name>.anim.json           → import as a JsonAsset (timing, pivots, events, direction map).
 *
 * Frame names in the plist match `frames[].name` in the JSON (e.g. "walk_east_03").
 * Pivots: `pivot_norm` is the logical root (feet) in the untrimmed frame, Y-up — it is applied as
 * the UITransform anchor so the node position is the character's ground point. Sprite.trim must be
 * false and sizeMode RAW so trimmed atlas frames keep their original (untrimmed) size and offset.
 *
 * Status: written against the documented Creator 3.x API (Sprite, SpriteAtlas, UITransform,
 * JsonAsset, Component.update). NOT yet compiled inside Creator on the development machine —
 * verify in your project (see docs/deployment-windows.md, Stage B).
 */
import { _decorator, Component, JsonAsset, Sprite, SpriteAtlas, UITransform, Vec2, Vec3 } from 'cc';
const { ccclass, property, requireComponent } = _decorator;

interface ExportFrame { name: string; duration_ms: number; start_ms: number; pivot_norm: [number, number]; }
interface ExportEvent { frame: number; type: string; name?: string; time_ms: number; data?: Record<string, unknown>; }
interface ExportAnimation { key: string; name: string; direction: string; loop: { enabled: boolean; hold_last?: boolean }; frames: ExportFrame[]; events: ExportEvent[]; }
interface ExportManifest { animations: ExportAnimation[]; direction_map: Record<string, Record<string, { key: string; flip_x: boolean }>>; }

export const ANIM_EVENT = 'artstudio-anim-event';
export const ANIM_FINISHED = 'artstudio-anim-finished';

@ccclass('DirectionalSpriteAnimator')
@requireComponent(Sprite)
export class DirectionalSpriteAnimator extends Component {
    @property(SpriteAtlas) atlas: SpriteAtlas | null = null;
    @property(JsonAsset) manifest: JsonAsset | null = null;
    @property defaultAnimation = 'idle';
    @property defaultDirection = 'south';
    @property speed = 1;

    private byKey = new Map<string, ExportAnimation>();
    private map: ExportManifest['direction_map'] = {};
    private current: ExportAnimation | null = null;
    private flip = false;
    private timeMs = 0;
    private frameIndex = -1;
    private playing = false;
    private baseScaleX = 1;

    onLoad() {
        const data = this.manifest?.json as ExportManifest | undefined;
        if (!data) { console.warn('DirectionalSpriteAnimator: manifest missing'); return; }
        for (const a of data.animations) this.byKey.set(a.key, a);
        this.map = data.direction_map;
        this.baseScaleX = Math.abs(this.node.scale.x) || 1;
        const sprite = this.getComponent(Sprite)!;
        sprite.trim = false;
        sprite.sizeMode = Sprite.SizeMode.RAW;
        this.play(this.defaultAnimation, this.defaultDirection);
    }

    /** Play `name` facing `direction` (e.g. walk/east). Falls back to direction "none" for non-directional clips. */
    play(name: string, direction: string, restart = false) {
        const dirs = this.map[name];
        const entry = dirs?.[direction] ?? dirs?.['none'];
        if (!entry) { console.warn(`No animation ${name}/${direction}`); return; }
        const anim = this.byKey.get(entry.key)!;
        if (!restart && anim === this.current && entry.flip_x === this.flip) return;
        this.current = anim; this.flip = entry.flip_x; this.timeMs = 0; this.frameIndex = -1; this.playing = true;
        const s = this.node.scale;
        this.node.setScale(new Vec3(this.flip ? -this.baseScaleX : this.baseScaleX, s.y, s.z));
        this.showFrame(0);
    }

    update(dt: number) {
        const a = this.current;
        if (!a || !this.playing) return;
        const total = a.frames.reduce((s, f) => s + f.duration_ms, 0);
        const prev = this.timeMs;
        this.timeMs += dt * 1000 * this.speed;
        // Fire every event whose time was crossed exactly once, even at low frame rates.
        for (const e of a.events) if (e.time_ms > prev && e.time_ms <= this.timeMs) this.node.emit(ANIM_EVENT, e, a.key);
        if (this.timeMs >= total) {
            if (a.loop.enabled) {
                this.timeMs %= total;
                for (const e of a.events) if (e.time_ms <= this.timeMs) this.node.emit(ANIM_EVENT, e, a.key);
            } else {
                this.timeMs = total - 1; this.playing = false;
                this.node.emit(ANIM_FINISHED, a.key);
            }
        }
        let acc = 0;
        for (let i = 0; i < a.frames.length; i++) {
            acc += a.frames[i].duration_ms;
            if (this.timeMs < acc) { this.showFrame(i); break; }
        }
    }

    private showFrame(i: number) {
        if (!this.current || i === this.frameIndex) return;
        this.frameIndex = i;
        const f = this.current.frames[i];
        const sf = this.atlas?.getSpriteFrame(f.name);
        if (!sf) { console.warn('Missing sprite frame', f.name); return; }
        this.getComponent(Sprite)!.spriteFrame = sf;
        this.getComponent(UITransform)!.setAnchorPoint(new Vec2(f.pivot_norm[0], f.pivot_norm[1]));
    }
}
