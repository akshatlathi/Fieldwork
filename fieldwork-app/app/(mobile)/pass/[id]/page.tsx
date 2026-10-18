import type { Metadata } from "next";
import { PassView } from "./PassView";

export const metadata: Metadata = { title: "Garment Pass" };

export default async function PassPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PassView id={id} />;
}
