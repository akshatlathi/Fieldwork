import type { Metadata } from "next";
import { UnboxView } from "./UnboxView";

export const metadata: Metadata = { title: "Check the unboxing" };

export default async function UnboxPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <UnboxView id={id} />;
}
