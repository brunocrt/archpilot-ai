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
      <body
        style={{
          fontFamily: "Arial, sans-serif",
          background: "#f5f5f5",
          margin: 0,
        }}
      >
        <div
          style={{
            maxWidth: "1100px",
            margin: "0 auto",
            padding: "20px",
          }}
        >
          <header style={{ marginBottom: "30px" }}>
            <h1>ArchPilot AI</h1>
            <p>Enterprise Architecture Copilot</p>

            <nav style={{ marginTop: "10px" }}>
              <Link href="/" style={{ marginRight: "15px" }}>
                Chat
              </Link>
              <Link href="/upload" style={{ marginRight: "15px" }}>
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