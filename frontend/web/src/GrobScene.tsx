import { useEffect, useRef } from "react";
import grobScene from "../../miniapp/src/assets/lotteries/grob-scene.webp";

export function GrobScene({ selected }: { selected: number[] }) {
  const host = useRef<HTMLDivElement>(null);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;

  useEffect(() => {
    let disposed = false;
    let game: import("phaser").Game | undefined;
    void import("phaser").then(({ default: Phaser }) => {
      if (disposed || !host.current) return;
      class CryptScene extends Phaser.Scene {
        private tombstones: import("phaser").GameObjects.Container[] = [];
        private background?: import("phaser").GameObjects.Image;
        preload() { this.load.image("crypt", grobScene); }
        create() {
          this.background = this.add.image(0, 0, "crypt").setOrigin(.5).setAlpha(.86);
          this.add.rectangle(0, 0, 1000, 700, 0x08050d, .4).setOrigin(0);
          for (let index = 0; index < 5; index += 1) { const bat = this.add.graphics({ x: 40 + index * 90, y: 35 + (index % 2) * 28 }); bat.lineStyle(2, 0xc57c82, .48).beginPath().moveTo(-18, 2).lineTo(-8, -9).lineTo(0, 0).lineTo(8, -9).lineTo(18, 2).strokePath(); this.tweens.add({ targets: bat, y: bat.y + 13, duration: 1800 + index * 170, yoyo: true, repeat: -1, ease: "Sine.inOut", delay: index * 170 }); }
          for (let index = 0; index < 6; index += 1) { const stone = this.add.container(0, 0); const glow = this.add.circle(0, 42, 30, 0xd66e67, 0).setBlendMode(Phaser.BlendModes.ADD); const plate = this.add.rectangle(0, 0, 72, 112, 0x160e19, .72).setStrokeStyle(1, 0x9c686e, .9); const number = this.add.text(0, 4, "?", { color: "#b58c93", fontFamily: "Prata, Georgia, serif", fontSize: "28px" }).setOrigin(.5); const mark = this.add.text(0, -37, "✦", { color: "#b87977", fontSize: "12px" }).setOrigin(.5); stone.add([glow, plate, number, mark]); this.tombstones.push(stone); }
          this.scale.on("resize", (size: import("phaser").Structs.Size) => this.layout(size)); this.layout(this.scale.gameSize); this.setSelected(selectedRef.current);
        }
        setSelected(values: number[]) { this.tombstones.forEach((stone, index) => { const value = values[index]; const plate = stone.getAt(1) as import("phaser").GameObjects.Rectangle; const number = stone.getAt(2) as import("phaser").GameObjects.Text; plate.setFillStyle(value ? 0xb96763 : 0x160e19, value ? .92 : .72); plate.setStrokeStyle(value ? 2 : 1, value ? 0xf0b49b : 0x9c686e); number.setText(value ? String(value).padStart(2, "0") : "?").setColor(value ? "#24131a" : "#b58c93"); }); }
        layout(size: import("phaser").Structs.Size) { const width = size.width; const height = size.height; this.background?.setPosition(width / 2, height / 2).setDisplaySize(width, height); this.tombstones.forEach((stone, index) => stone.setPosition(width * (.12 + index * .152), height * .68)); }
      }
      game = new Phaser.Game({ type: Phaser.CANVAS, parent: host.current, width: 600, height: 300, transparent: true, render: { antialias: true, pixelArt: false }, scale: { mode: Phaser.Scale.RESIZE, autoCenter: Phaser.Scale.CENTER_BOTH }, scene: CryptScene });
    });
    return () => { disposed = true; game?.destroy(true); };
  }, []);
  return <div className="grob-scene-canvas" ref={host} aria-hidden="true" />;
}
