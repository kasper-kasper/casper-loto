import { Composition, Folder } from "remotion";
import { CasperReel } from "./Composition";
import { Hook } from "./Hook";
import { Free } from "./Free";
import { Choose } from "./Choose";
import { Discover } from "./Discover";
import { Suspense } from "./Suspense";
import { Finale } from "./Finale";
export const RemotionRoot = () => (
  <>
    <Composition
      id="Casper-Reel"
      component={CasperReel}
      durationInFrames={720}
      fps={30}
      width={1080}
      height={1920}
    />
    <Folder name="Scenes">
      <Composition
        id="Hook"
        component={Hook}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Free"
        component={Free}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Choose"
        component={Choose}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Discover"
        component={Discover}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Suspense"
        component={Suspense}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Finale"
        component={Finale}
        durationInFrames={180}
        fps={30}
        width={1080}
        height={1920}
      />
    </Folder>
  </>
);
