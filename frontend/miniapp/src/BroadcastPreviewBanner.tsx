import { tr } from "./i18n";
import { broadcastPreviewConfig } from "./broadcastPreview";

export function BroadcastPreviewBanner() {
  if (!broadcastPreviewConfig()) return null;
  return <div className="broadcast-preview-banner" role="status"><b>{tr("ТЕСТОВЫЙ ЭФИР")}</b><span>{tr("Деньги, билеты и настоящие тиражи не затрагиваются")}</span></div>;
}
