import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useTenantRefetch } from "../hooks";
import { emit } from "../helpers";

// Contract (S-T2): useTenantRefetch(fetcher) refetches whenever
// TenantSelector emits 'tenant:changed' on the helpers event bus, and
// always calls the LATEST fetcher (a non-memoized one is fine).

function Probe({ fetcher }: { fetcher: () => void }) {
  useTenantRefetch(fetcher);
  return <div>probe</div>;
}

describe("useTenantRefetch", () => {
  it("calls the fetcher when tenant:changed is emitted", async () => {
    const fetcher = vi.fn();
    render(<Probe fetcher={fetcher} />);

    expect(fetcher).not.toHaveBeenCalled();
    emit("tenant:changed", "north");
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });

  it("does not refetch on unrelated events", async () => {
    const fetcher = vi.fn();
    render(<Probe fetcher={fetcher} />);

    document.body.dispatchEvent(new CustomEvent("other:event"));
    emit("tenant:changed", "main");
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });

  it("uses the latest fetcher after a re-render", async () => {
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = render(<Probe fetcher={first} />);

    rerender(<Probe fetcher={second} />);
    emit("tenant:changed", "north");
    await waitFor(() => expect(second).toHaveBeenCalledTimes(1));
    expect(first).not.toHaveBeenCalled();
  });
});
