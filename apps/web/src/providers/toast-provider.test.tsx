import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider, useToast } from "./toast-provider";

function Trigger() {
  const { showToast } = useToast();
  return (
    <button onClick={() => showToast("Saved for later.")}>notify</button>
  );
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ToastProvider", () => {
  it("shows a toast and auto-dismisses it after 2.6s", () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "notify" }));
    expect(screen.getByRole("status")).toHaveTextContent("Saved for later.");

    act(() => {
      vi.advanceTimersByTime(2599);
    });
    expect(screen.getByRole("status")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
