/**
 * Safely extract a human-readable string from an Axios error response.
 *
 * FastAPI returns `detail` as either a plain string (HTTPException) or an
 * array of validation-error objects [{type, loc, msg, input, url}] on 422
 * responses.  This helper normalises both shapes into a single string so they
 * can be safely rendered as React children.
 */

export function extractErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as any)?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: any) => {
        const msg = d?.msg || (typeof d === "string" ? d : JSON.stringify(d));
        const loc = d?.loc;
        if (Array.isArray(loc) && loc.length > 0) {
          const field = loc[loc.length - 1];
          return `${field}: ${msg}`;
        }
        return msg;
      })
      .join("; ");
  }

  const message = (err as any)?.response?.data?.message;
  if (typeof message === "string") {
    return message;
  }

  if ((err as any)?.message && typeof (err as any).message === "string") {
    return (err as any).message;
  }

  return fallback;
}
