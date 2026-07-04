import { Suspense } from "react";

import { InboxScreen } from "@/components/jobs/inbox-screen";

export default function InboxPage() {
  // Suspense boundary required for useSearchParams in a statically
  // rendered route.
  return (
    <Suspense>
      <InboxScreen />
    </Suspense>
  );
}
