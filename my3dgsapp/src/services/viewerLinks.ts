export function openCompareViewer(baseUrl: string, studioJobId: number): string {
  return `${trimSlash(baseUrl)}/viewer_compare_splat_mesh.html?studio_job_id=${encodeURIComponent(studioJobId)}`;
}

export function openDeliveryPage(baseUrl: string, jobId: number): string {
  return `${trimSlash(baseUrl)}/delivery.php?job_id=${encodeURIComponent(jobId)}`;
}

function trimSlash(value: string): string {
  return value.replace(/\/+$/, "");
}
