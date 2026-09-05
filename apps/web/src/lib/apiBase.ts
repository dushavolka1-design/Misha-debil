export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const injected = (window as unknown as { __DOCLY_API__?: string }).__DOCLY_API__;
    if (injected) {
      return injected.replace(/\/$/, "");
    }
  }
  const runtime = process.env.API_PUBLIC_BASE_URL;
  if (runtime) {
    return runtime.replace(/\/$/, "");
  }
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}
