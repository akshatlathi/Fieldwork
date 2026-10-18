import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./tokens.css";
import "./globals.css";
import "./identity.css";
const instrument = localFont({ src: "../public/fonts/InstrumentSans.ttf", variable: "--font-instrument", display: "swap", weight: "400 700" });
export const metadata: Metadata = { title: { default: "Fieldwork · Pieces with a story", template: "%s · Fieldwork" }, description: "Discover second-hand garments through condition records and image evidence, with human review of buyer-reported issues. Prototype: payments are simulated.", manifest: "/manifest.webmanifest", appleWebApp: { capable: true, statusBarStyle: "default", title: "Fieldwork" } };
export const viewport: Viewport = { width:"device-width", initialScale:1, viewportFit:"cover", themeColor:"#EDE7DF" };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en" className={instrument.variable}><body>{process.env.NEXT_PUBLIC_FIELDWORK_PREVIEW==="1"&&<div className="fw-preview-label">DESIGN PREVIEW · SAMPLE DATA · NO LIVE AI OR PAYMENTS</div>}{children}</body></html>; }
