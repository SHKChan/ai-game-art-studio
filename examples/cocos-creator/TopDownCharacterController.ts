/**
 * Cocos Creator 3.x — directional movement driving DirectionalSpriteAnimator.
 * WASD / arrow keys move; J attacks. Supports 4- or 8-direction sets and side-scrollers
 * (directions "left"/"right"). World movement is done here in code; art frames stay in place
 * (root motion is not baked into frames), matching the exporter's pivot convention.
 * Status: unverified inside Creator on the development machine (Stage B).
 */
import { _decorator, Component, EventKeyboard, Input, input, KeyCode, Vec3 } from 'cc';
import { ANIM_EVENT, ANIM_FINISHED, DirectionalSpriteAnimator } from './DirectionalSpriteAnimator';
const { ccclass, property } = _decorator;

const EIGHT = ['east', 'north_east', 'north', 'north_west', 'west', 'south_west', 'south', 'south_east'];
const FOUR = ['east', 'north', 'west', 'south'];

@ccclass('TopDownCharacterController')
export class TopDownCharacterController extends Component {
    @property(DirectionalSpriteAnimator) animator: DirectionalSpriteAnimator | null = null;
    @property moveSpeed = 120;
    @property directions = 4;          // 2 (side-scroller), 4 or 8
    @property walkAnimation = 'walk';
    @property idleAnimation = 'idle';
    @property attackAnimation = 'attack';

    private keys = new Set<KeyCode>();
    private facing = 'south';
    private attacking = false;

    onEnable() {
        input.on(Input.EventType.KEY_DOWN, this.onDown, this);
        input.on(Input.EventType.KEY_UP, this.onUp, this);
        this.animator?.node.on(ANIM_FINISHED, this.onFinished, this);
        this.animator?.node.on(ANIM_EVENT, this.onEvent, this);
        if (this.directions === 2) this.facing = 'right';
    }

    onDisable() {
        input.off(Input.EventType.KEY_DOWN, this.onDown, this);
        input.off(Input.EventType.KEY_UP, this.onUp, this);
        this.animator?.node.off(ANIM_FINISHED, this.onFinished, this);
        this.animator?.node.off(ANIM_EVENT, this.onEvent, this);
    }

    private onDown(e: EventKeyboard) {
        this.keys.add(e.keyCode);
        if (e.keyCode === KeyCode.KEY_J && !this.attacking) {
            this.attacking = true;
            this.animator?.play(this.attackAnimation, this.facing, true);
        }
    }
    private onUp(e: EventKeyboard) { this.keys.delete(e.keyCode); }
    private onFinished(key: string) { if (this.attacking) this.attacking = false; }
    private onEvent(ev: { type: string; frame: number }, key: string) {
        if (ev.type === 'hit') { /* enable hitbox for this attack phase here */ }
    }

    update(dt: number) {
        const k = this.keys;
        const x = (k.has(KeyCode.KEY_D) || k.has(KeyCode.ARROW_RIGHT) ? 1 : 0) - (k.has(KeyCode.KEY_A) || k.has(KeyCode.ARROW_LEFT) ? 1 : 0);
        const y = this.directions === 2 ? 0 : (k.has(KeyCode.KEY_W) || k.has(KeyCode.ARROW_UP) ? 1 : 0) - (k.has(KeyCode.KEY_S) || k.has(KeyCode.ARROW_DOWN) ? 1 : 0);
        if (this.attacking) return;
        if (x === 0 && y === 0) { this.animator?.play(this.idleAnimation, this.facing); return; }
        this.facing = this.directionFor(x, y);
        const len = Math.hypot(x, y);
        const p = this.node.position;
        this.node.setPosition(new Vec3(p.x + (x / len) * this.moveSpeed * dt, p.y + (y / len) * this.moveSpeed * dt, p.z));
        this.animator?.play(this.walkAnimation, this.facing);
    }

    private directionFor(x: number, y: number): string {
        if (this.directions === 2) return x < 0 ? 'left' : 'right';
        const angle = Math.atan2(y, x);
        const set = this.directions === 8 ? EIGHT : FOUR;
        const step = (Math.PI * 2) / set.length;
        const idx = Math.round(((angle + Math.PI * 2) % (Math.PI * 2)) / step) % set.length;
        return set[idx];
    }
}
