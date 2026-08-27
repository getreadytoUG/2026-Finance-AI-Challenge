"use client";

import { useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";

type PasswordFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export default function PasswordField({ label, value, onChange, placeholder = "••••••••" }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);

  return (
    <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
      {label}
      <div className="relative">
        <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={17} strokeWidth={1.8} />
        <input
          className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-11 pr-12 text-[13px] font-semibold outline-none transition placeholder:text-slate-400 focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          type={visible ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "비밀번호 숨기기" : "비밀번호 표시"}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 hover:bg-slate-50"
        >
          {visible ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
    </label>
  );
}
