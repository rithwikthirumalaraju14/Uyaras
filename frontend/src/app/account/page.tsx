import Account from "@/components/account";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <Account initialToken={token || ""} />;
}
