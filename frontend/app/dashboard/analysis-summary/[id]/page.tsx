import { redirect } from 'next/navigation';

type Props = {
  params: Promise<{ id: string }>;
};

export default async function UserAnalysisSummaryLegacyAliasPage({ params }: Props) {
  const { id } = await params;
  redirect(`/dashboard/analysis/${id}/summary`);
}
