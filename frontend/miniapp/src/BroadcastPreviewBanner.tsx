import { broadcastPreviewConfig } from "./broadcastPreview";

export function BroadcastPreviewBanner() {
  if (!broadcastPreviewConfig()) return null;
  return <div className="broadcast-preview-banner" role="status"><b>ТЕСТОВЫЙ ЭФИР</b><span>Деньги, билеты и настоящие тиражи не затрагиваются</span></div>;
}
