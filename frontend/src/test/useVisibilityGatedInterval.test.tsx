import React from "react";
import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useVisibilityGatedInterval } from "../hooks";

// Contract (R1-04 / US-R08-07): useVisibilityGatedInterval(fetcher, ms)
// polls every ms while the tab is visible, pauses while hidden, fetches
// immediately on return to the tab, and clears the timer on unmount.

function Probe({ fetcher, ms }: { fetcher: () => void; ms: number }) {
  useVisibilityGatedInterval(fetcher, ms);
  return <div>probe</div>;
}

let hidden = false;
const originalHidden = Object.getOwnPropertyDescriptor(document, "hidden");

function setHidden(value: boolean) {
  hidden = value;
  Object.defineProperty(document, "hidden", {
    configurable: true,
    get: () => hidden,
  });
}

function fireVisibilityChange() {
  document.dispatchEvent(new Event("visibilitychange"));
}

afterEach(() => {
  vi.useRealTimers();
  if (originalHidden) {
    Object.defineProperty(document, "hidden", originalHidden);
  } else {
    setHidden(false);
  }
});

describe("useVisibilityGatedInterval", () => {
  it("polls the fetcher every ms", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn();
    render(<Probe fetcher={fetcher} ms={30000} />);

    expect(fetcher).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(30000);
    expect(fetcher).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(30000);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("stops polling while the tab is hidden and refetches on return", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn();
    setHidden(true);
    render(<Probe fetcher={fetcher} ms={30000} />);
    fireVisibilityChange();

    await vi.advanceTimersByTimeAsync(90000);
    expect(fetcher).not.toHaveBeenCalled();

    setHidden(false);
    fireVisibilityChange();
    expect(fetcher).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(30000);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("clears the interval on unmount", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn();
    const { unmount } = render(<Probe fetcher={fetcher} ms={30000} />);

    unmount();
    await vi.advanceTimersByTimeAsync(90000);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("re-arms with the new cadence when ms changes", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn();
    const { rerender } = render(<Probe fetcher={fetcher} ms={30000} />);

    rerender(<Probe fetcher={fetcher} ms={10000} />);
    await vi.advanceTimersByTimeAsync(10000);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
