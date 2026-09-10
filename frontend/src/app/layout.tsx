import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EffiGov Case Management",
  description: "Staff dashboard for EffiGov service cases",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
