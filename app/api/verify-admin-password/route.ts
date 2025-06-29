import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { password } = await req.json();
  // 读取环境变量
  const adminPassword = process.env.ADMIN_SETTING_PASSWORD;
  if (password === adminPassword) {
    return NextResponse.json({ ok: true });
  } else {
    return NextResponse.json({ ok: false, msg: "密码错误" }, { status: 401 });
  }
}
