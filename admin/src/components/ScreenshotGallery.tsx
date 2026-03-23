import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  getScreenshotBlob,
  listAttemptScreenshots,
  type ScreenshotListItem,
} from "../lib/api";

type ScreenshotWithPreview = ScreenshotListItem & {
  previewUrl: string;
};

type Props = {
  attemptId: string | null;
  title?: string;
  description?: string;
  onAuthError?: (message: string) => void;
};

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function ScreenshotGallery({
  attemptId,
  title = "Screenshots",
  description = "Periodic screenshot evidence captured for this attempt.",
  onAuthError,
}: Props) {
  const [screenshots, setScreenshots] = useState<ScreenshotWithPreview[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedScreenshotId, setSelectedScreenshotId] = useState<string | null>(null);
  const screenshotUrlsRef = useRef<string[]>([]);

  useEffect(() => {
    return () => {
      screenshotUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      screenshotUrlsRef.current = [];
    };
  }, []);

  useEffect(() => {
    if (!attemptId) {
      setError(null);
      setSelectedScreenshotId(null);
      screenshotUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      screenshotUrlsRef.current = [];
      setScreenshots([]);
      return;
    }

    let cancelled = false;
    const resolvedAttemptId = attemptId;

    async function load() {
      setLoading(true);
      setError(null);
      setSelectedScreenshotId(null);
      try {
        const items = await listAttemptScreenshots(resolvedAttemptId);
        const ordered = [...items].sort((a, b) => b.captured_at.localeCompare(a.captured_at));
        const withPreviews = await Promise.all(
          ordered.map(async (item) => {
            const blob = await getScreenshotBlob(item.id);
            return {
              ...item,
              previewUrl: URL.createObjectURL(blob),
            };
          }),
        );
        if (cancelled) {
          withPreviews.forEach((item) => URL.revokeObjectURL(item.previewUrl));
          return;
        }
        screenshotUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
        screenshotUrlsRef.current = withPreviews.map((item) => item.previewUrl);
        setScreenshots(withPreviews);
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Could not load screenshots";
        setError(message);
        screenshotUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
        screenshotUrlsRef.current = [];
        setScreenshots([]);
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          onAuthError?.("Authentication failed or insufficient permissions. Please login as admin.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [attemptId, onAuthError]);

  const selectedScreenshot = useMemo(
    () => screenshots.find((item) => item.id === selectedScreenshotId) ?? null,
    [screenshots, selectedScreenshotId],
  );

  async function onRefresh() {
    if (!attemptId) {
      return;
    }
    const resolvedAttemptId = attemptId;
    setRefreshing(true);
    setError(null);
    try {
      const items = await listAttemptScreenshots(resolvedAttemptId);
      const ordered = [...items].sort((a, b) => b.captured_at.localeCompare(a.captured_at));
      const withPreviews = await Promise.all(
        ordered.map(async (item) => {
          const blob = await getScreenshotBlob(item.id);
          return {
            ...item,
            previewUrl: URL.createObjectURL(blob),
          };
        }),
      );
      setSelectedScreenshotId((current) =>
        current && withPreviews.some((item) => item.id === current) ? current : null,
      );
      screenshotUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      screenshotUrlsRef.current = withPreviews.map((item) => item.previewUrl);
      setScreenshots(withPreviews);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not refresh screenshots";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError?.("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <section className="panel screenshot-panel">
      <div className="section-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <div className="screenshot-toolbar">
          <span className="status-pill">{screenshots.length} shots</span>
          <button
            type="button"
            className="secondary-button"
            onClick={() => void onRefresh()}
            disabled={!attemptId || loading || refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh screenshots"}
          </button>
        </div>
      </div>

      {!attemptId && <p className="state-text">Select an attempt to review screenshots.</p>}
      {attemptId && loading && <p className="state-text">Loading screenshots...</p>}
      {error && <p className="error">Error: {error}</p>}
      {attemptId && !loading && !error && screenshots.length === 0 && (
        <div className="screenshot-empty-state">
          <strong>No screenshots available</strong>
          <p>No screenshot evidence has been uploaded for this attempt yet.</p>
        </div>
      )}

      {attemptId && !loading && !error && screenshots.length > 0 && (
        <div className="screenshot-gallery">
          {screenshots.map((item) => (
            <button
              key={item.id}
              type="button"
              className="screenshot-card"
              onClick={() => setSelectedScreenshotId(item.id)}
            >
              <img src={item.previewUrl} alt={`Attempt screenshot captured at ${formatTimestamp(item.captured_at)}`} />
              <div className="screenshot-card-meta">
                <strong>{formatTimestamp(item.captured_at)}</strong>
                <span className="mono">{item.id.slice(0, 8)}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {selectedScreenshot && (
        <div
          className="lightbox-backdrop"
          role="presentation"
          onClick={() => setSelectedScreenshotId(null)}
        >
          <div
            className="lightbox-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Screenshot preview"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="lightbox-header">
              <div>
                <h3>Screenshot Preview</h3>
                <p>{formatTimestamp(selectedScreenshot.captured_at)}</p>
              </div>
              <button type="button" className="secondary-button" onClick={() => setSelectedScreenshotId(null)}>
                Close
              </button>
            </div>
            <div className="lightbox-body">
              <img
                src={selectedScreenshot.previewUrl}
                alt={`Screenshot captured at ${formatTimestamp(selectedScreenshot.captured_at)}`}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default ScreenshotGallery;
