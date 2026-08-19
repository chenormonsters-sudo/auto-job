import Link from "next/link";

const links = [
  { href: "/", label: "工作台" },
  { href: "/resumes", label: "简历" },
  { href: "/jobs", label: "职位" },
  { href: "/review", label: "审查" },
  { href: "/delivery", label: "投递" },
  { href: "/platforms", label: "平台" },
];

export default function Nav() {
  return (
    <nav className="nav">
      <strong>求职工作台</strong>
      {links.map((link) => (
        <Link key={link.href} href={link.href}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
