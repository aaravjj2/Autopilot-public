import { redirect } from "next/navigation";

export default async function LegacyPortfolioRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/dashboard/marketplace/${id}`);
}
