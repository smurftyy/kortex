import { JobDetailScreen } from "@/components/jobs/job-detail-screen";

export default function JobDetailPage({
  params,
}: {
  params: { jobId: string };
}) {
  return <JobDetailScreen jobId={params.jobId} />;
}
