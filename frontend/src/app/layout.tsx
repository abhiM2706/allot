import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tabbed",
  description: "T&E tied to the customer it was for.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
