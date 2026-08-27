import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import StudyBookmarks from "../radiologist/StudyBookmarks";

vi.mock("../api/ris", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/ris")>();
  return {
    ...actual,
    listBookmarkCollections: vi.fn(),
    createBookmarkCollection: vi.fn(),
    listStudyBookmarks: vi.fn(),
    createStudyBookmark: vi.fn(),
    deleteStudyBookmark: vi.fn(),
  };
});

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useTenantRefetch: vi.fn(),
}));

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({ hasPermission: () => true }),
  };
});

import {
  listBookmarkCollections,
  createBookmarkCollection,
  listStudyBookmarks,
  createStudyBookmark,
  deleteStudyBookmark,
} from "../api/ris";
const mockListCollections = vi.mocked(listBookmarkCollections);
const mockCreateCollection = vi.mocked(createBookmarkCollection);
const mockListBookmarks = vi.mocked(listStudyBookmarks);
const mockCreateBookmark = vi.mocked(createStudyBookmark);
const mockDeleteBookmark = vi.mocked(deleteStudyBookmark);

function renderBookmarks() {
  localStorage.setItem("userId", "50");
  localStorage.setItem("username", "test");
  localStorage.setItem("permissions", JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]));
  localStorage.setItem("tenant_id", "t1");
  return render(
    <MemoryRouter>
      <App>
        <AuthProvider>
          <ThemeProvider>
            <StudyBookmarks />
          </ThemeProvider>
        </AuthProvider>
      </App>
    </MemoryRouter>
  );
}

const mockCollection: import("../api/ris").BookmarkCollection = {
  id: "bc-1",
  user_id: "50",
  name: "Teaching Cases",
  description: "Interesting cases for teaching",
  is_shared: false,
  created_at: "2026-08-22T10:00:00Z",
};

const mockBookmark: import("../api/ris").StudyBookmark = {
  id: "bm-1",
  user_id: "50",
  study_uid: "1.2.3.4",
  study_desc: "Chest CT — rare finding",
  collection_id: "bc-1",
  notes: "Check follow-up",
  created_at: "2026-08-22T10:00:00Z",
};

describe("StudyBookmarks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListCollections.mockResolvedValue([mockCollection]);
    mockListBookmarks.mockResolvedValue([mockBookmark]);
  });

  it("renders bookmarks with study description", async () => {
    renderBookmarks();
    await waitFor(() => {
      expect(screen.getByText(/Chest CT — rare finding/)).toBeInTheDocument();
    });
    expect(screen.getByText("Teaching Cases")).toBeInTheDocument();
  });

  it("loads bookmarks and collections on mount", async () => {
    renderBookmarks();
    await waitFor(() => {
      expect(mockListCollections).toHaveBeenCalled();
      expect(mockListBookmarks).toHaveBeenCalled();
    });
  });

  it("creates a new collection from the modal", async () => {
    mockCreateCollection.mockResolvedValue(mockCollection);
    renderBookmarks();
    await waitFor(() => {
      expect(screen.getByText("New Collection")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("New Collection")[0]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create collection/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Collection Name/), {
      target: { value: "Research" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create collection/i }));

    await waitFor(() => {
      expect(mockCreateCollection).toHaveBeenCalledWith({
        name: "Research",
        description: "",
      });
    });
  });

  it("bookmarks a study from the modal", async () => {
    mockCreateBookmark.mockResolvedValue(mockBookmark);
    renderBookmarks();
    await waitFor(() => {
      expect(screen.getByText("Bookmark Study")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("Bookmark Study")[0]);
    const dialog = screen.getAllByRole("dialog").find((d) => d.textContent?.includes("Study UID"))!;
    await waitFor(() => {
      expect(dialog).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Study UID/), {
      target: { value: "1.2.3.4" },
    });
    fireEvent.click(dialog.querySelector('button[type="submit"]') as HTMLElement);

    await waitFor(() => {
      expect(mockCreateBookmark).toHaveBeenCalledWith({
        study_uid: "1.2.3.4",
        study_desc: "",
        collection_id: "",
        notes: "",
      });
    });
  });

  it("removes a bookmark from the row action", async () => {
    mockDeleteBookmark.mockResolvedValue(undefined);
    renderBookmarks();
    await waitFor(() => {
      expect(screen.getByText("Remove")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Remove"));
    fireEvent.click(await screen.findByRole("button", { name: /^remove$/i }));

    await waitFor(() => {
      expect(mockDeleteBookmark).toHaveBeenCalledWith("bm-1");
    });
  });

  it("renders empty state when no bookmarks exist", async () => {
    mockListBookmarks.mockResolvedValue([]);
    renderBookmarks();
    await waitFor(() => {
      expect(screen.getByText(/No bookmarked studies yet/i)).toBeInTheDocument();
    });
  });
});
