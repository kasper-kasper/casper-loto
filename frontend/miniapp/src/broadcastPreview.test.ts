import { broadcastPreviewConfig } from "./broadcastPreview";

describe("broadcast rehearsal route", () => {
  it("accepts standard lotteries and a safe result scenario", () => {
    window.history.replaceState({}, "", "/?broadcast-preview=khan&scenario=loss");
    expect(broadcastPreviewConfig()).toEqual({ lotteryCode: "khan", scenario: "loss" });
  });

  it("rejects Fast and unknown lottery codes", () => {
    window.history.replaceState({}, "", "/?broadcast-preview=flash&scenario=win");
    expect(broadcastPreviewConfig()).toBeNull();
  });
});
