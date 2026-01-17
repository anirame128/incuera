import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import IncueraProvider from "./components/IncueraProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ShopHub - E-commerce Demo",
  description: "Demo e-commerce store with session replay",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <IncueraProvider
          apiKey={process.env.NEXT_PUBLIC_INCUERA_API_KEY}
          apiHost={process.env.NEXT_PUBLIC_INCUERA_API_HOST || "http://localhost:8000"}
          debug={process.env.NODE_ENV === "development"}
        />
        {children}
      </body>
    </html>
  );
}
