import { redirect } from 'next/navigation';

type Props = {
  params: Promise<{ id: string }>;
};

export default async function AdminAnalysisSingularSummaryAliasPage({ params }: Props) {
  const { id } = await params;
  redirect(`/dashboard/admin/analyses/${id}/summary`);
}
