import type { Metadata, Viewport } from "next";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kolkata Bus Router",
  description:
    "Find direct buses, one-change routes, and two-change routes across Kolkata's private & government bus network.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Kolkata Bus",
    statusBarStyle: "default",
  },
  icons: {
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "Kolkata Bus Router",
    description:
      "Find direct buses, one-change routes, and two-change routes across Kolkata's private & government bus network.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#1f6f4a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Hanken+Grotesque:wght@400;500;600;700&family=Spline+Sans+Mono:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
