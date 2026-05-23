import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ArchPilot AI",
  description: "Enterprise Architecture Copilot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <div>
              <h1>ArchPilot AI</h1>
              <p>Enterprise Architecture Copilot</p>
            </div>

            <nav className="app-nav">
              <Link href="/">
                Chat
              </Link>
              <Link href="/upload">
                Upload
              </Link>
              <Link href="/history">History</Link>
            </nav>
          </header>

          {children}
        </div>
      </body>
    </html>
  );
}
