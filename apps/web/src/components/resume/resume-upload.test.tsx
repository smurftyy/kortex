import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";

import { ResumeUpload } from "./resume-upload";

const uploadResume = vi.fn();
const parseResume = vi.fn();
vi.mock("@/lib/api/endpoints", () => ({
  uploadResume: (...args: unknown[]) => uploadResume(...args),
  parseResume: (...args: unknown[]) => parseResume(...args),
}));

function pdfFile(name = "resume.pdf", size = 1024): File {
  const file = new File(["%PDF-1.4"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ResumeUpload", () => {
  it("uploads then parses, and shows the extracted-text state", async () => {
    uploadResume.mockResolvedValue({ resume_url: "signed-url" });
    parseResume.mockResolvedValue({
      status: "parsed",
      resume_text: "Ada Lovelace — Analyst. Skills: math, engines.",
    });
    const user = userEvent.setup();
    render(<ResumeUpload />);

    await user.upload(screen.getByLabelText(/resume file/i), pdfFile());

    expect(await screen.findByText(/resume\.pdf uploaded/i)).toBeInTheDocument();
    expect(uploadResume).toHaveBeenCalledWith(expect.any(File));
    expect(parseResume).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/ada lovelace — analyst/i)).toBeInTheDocument();
  });

  it("shows the password-protected outcome without treating it as an error", async () => {
    uploadResume.mockResolvedValue({ resume_url: "signed-url" });
    parseResume.mockResolvedValue({
      status: "password_protected",
      resume_text: null,
    });
    const user = userEvent.setup();
    render(<ResumeUpload />);

    await user.upload(screen.getByLabelText(/resume file/i), pdfFile());

    expect(
      await screen.findByText(/password-protected/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload a different file/i }),
    ).toBeInTheDocument();
  });

  it("surfaces API upload errors and returns to the dropzone", async () => {
    uploadResume.mockRejectedValue(
      new ApiError(422, "RESUME_TOO_LARGE", "Resume exceeds the 5MB limit"),
    );
    const user = userEvent.setup();
    render(<ResumeUpload />);

    await user.upload(screen.getByLabelText(/resume file/i), pdfFile());

    expect(
      await screen.findByText(/exceeds the 5mb limit/i),
    ).toBeInTheDocument();
    expect(parseResume).not.toHaveBeenCalled();
    expect(
      screen.getByText(/drag and drop your resume/i),
    ).toBeInTheDocument();
  });

  it("rejects non-PDF files client-side without calling the API", async () => {
    // applyAccept off so the file reaches our own validation, mirroring a
    // drag-and-drop of an arbitrary file.
    const user = userEvent.setup({ applyAccept: false });
    render(<ResumeUpload />);

    const doc = new File(["hello"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await user.upload(screen.getByLabelText(/resume file/i), doc);

    expect(
      await screen.findByText(/only pdf files are supported/i),
    ).toBeInTheDocument();
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it("rejects oversized files client-side without calling the API", async () => {
    const user = userEvent.setup();
    render(<ResumeUpload />);

    await user.upload(
      screen.getByLabelText(/resume file/i),
      pdfFile("big.pdf", 6 * 1024 * 1024),
    );

    expect(await screen.findByText(/over the 5MB limit/i)).toBeInTheDocument();
    expect(uploadResume).not.toHaveBeenCalled();
  });
});
