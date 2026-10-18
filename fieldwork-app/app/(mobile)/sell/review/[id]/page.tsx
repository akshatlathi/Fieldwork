import type { Metadata } from "next";
import { SellerReviewView } from "./SellerReviewView";

export const metadata: Metadata = { title: "Review seller draft" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SellerReviewView id={id} />;
}
