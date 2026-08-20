import { Bell } from "lucide-react";
import { IconButton } from "./IconButton";

export const NotificationButton = ({ hasUnread = true }) => {
  return (
    <IconButton icon={Bell} badge={hasUnread} />
  );
};
