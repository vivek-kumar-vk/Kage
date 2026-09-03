import type { Metadata } from "next";
import { Inter, Fraunces, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// next/font hashes the family name, so every face is exposed as a CSS variable
// and referenced through it (globals.css + tailwind.config.ts). Naming the
// family literally would silently fall back to Georgia / ui-monospace.
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-serif",
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Finance OS",
  description: "Personal finance operating system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${fraunces.variable} ${jetbrains.variable} font-sans bg-carbon-dark text-gray-200`}
      >
        {children}
      </body>
    </html>
  );
}
