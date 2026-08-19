import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button } from "antd";
import React from "react";

/**
 * Shared prev/Today/next day navigation. Extracted from CalendarView and
 * ScheduleBoard to eliminate duplication (S1/D2 from the 3-agent review).
 *
 * - `onDayChange(delta)` — called with -1/+1 for prev/next
 * - `onToday()` — called when the Today button is clicked; each parent
 *   sets the day in its own timezone convention (UTC for CalendarView,
 *   browser-local for ScheduleBoard).
 */
export default function ScheduleDayNav({
  onDayChange,
  onToday,
}: {
  onDayChange: (delta: number) => void;
  onToday: () => void;
}) {
  return (
    <>
      <Button
        icon={<LeftOutlined />}
        onClick={() => onDayChange(-1)}
        aria-label="Previous day"
      />
      <Button onClick={onToday}>Today</Button>
      <Button
        icon={<RightOutlined />}
        onClick={() => onDayChange(1)}
        aria-label="Next day"
      />
    </>
  );
}
