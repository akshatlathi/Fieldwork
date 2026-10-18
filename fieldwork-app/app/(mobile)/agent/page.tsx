import type { Metadata } from "next";
import { AgentView } from "./AgentView";

export const metadata: Metadata = { title: "Shopping agent" };

export default function AgentPage() {
  return <AgentView />;
}
