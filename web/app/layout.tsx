import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

const title = "Auditable NL2SQL · 从问题到证据链";
const description =
  "用一个可回查的合成数据 run，展示自然语言问题、SQL、只读执行、证据指纹与回答如何绑定。";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") || host.startsWith("127.0.0.1")
      ? "http"
      : "https");
  const origin = new URL(`${protocol}://${host}`);
  const socialImage = new URL("/og.png", origin).toString();

  return {
    metadataBase: origin,
    title,
    description,
    applicationName: "Auditable NL2SQL Agent",
    openGraph: {
      type: "website",
      url: origin,
      title,
      description,
      locale: "zh_CN",
      images: [
        {
          url: socialImage,
          width: 1536,
          height: 1024,
          alt: "Auditable NL2SQL — 从问题到证据链",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [socialImage],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
