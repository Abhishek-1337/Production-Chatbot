const ICONS: Record<string, string> = {
  plus: "M12 5v14M5 12h14",
  search: "m21 21-4.3-4.3m2.3-5.2a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0",
  upload: "M12 16V4m0 0L7 9m5-5 5 5M5 20h14",
  send: "m22 2-7 20-4-9-9-4Z M22 2 11 13",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z M14 2v6h6",
  menu: "M4 6h16M4 12h16M4 18h16",
  logout: "M10 17l5-5-5-5M15 12H3M21 19V5a2 2 0 0 0-2-2h-4",
  book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5V5a2.5 2.5 0 0 1 2.5-2H20v14H6.5A2.5 2.5 0 0 0 4 19.5Z",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  close: "M6 6l12 12M18 6 6 18",
  check: "m5 12 4 4L19 6",
  alert:
    "M12 9v4m0 4h.01M10.3 3.8 2.1 18a2 2 0 0 0 1.7 3h16.4a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z",
  moon: "M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z",
  sun: "M12 3v2m0 14v2M5.6 5.6l1.4 1.4m10 10 1.4 1.4M3 12h2m14 0h2M5.6 18.4 7 17m10-10 1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
};

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}
