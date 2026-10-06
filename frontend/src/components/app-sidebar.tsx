"use client"

import {
  ActivityIcon,
  FilePlus2Icon,
  LayoutDashboardIcon,
  ListChecksIcon,
  SearchIcon,
  StethoscopeIcon,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

type NavItem = { title: string; href: string; icon: React.ComponentType; match?: (path: string) => boolean }

/** Grouped by what the user is doing: overview, the coding workflow
 *  (submit -> review), terminology lookup, and system health. */
const NAV: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ title: "Dashboard", href: "/", icon: LayoutDashboardIcon, match: (p) => p === "/" }],
  },
  {
    label: "Coding",
    items: [
      { title: "New encounter", href: "/coding/new", icon: FilePlus2Icon },
      {
        title: "Review queue",
        href: "/coding/encounters",
        icon: ListChecksIcon,
        match: (p) => p.startsWith("/coding/encounters"),
      },
    ],
  },
  {
    label: "Terminology",
    items: [
      {
        title: "ICD-10-CM search",
        href: "/terminology",
        icon: SearchIcon,
        match: (p) => p.startsWith("/terminology"),
      },
    ],
  },
  {
    label: "System",
    items: [{ title: "Status & engines", href: "/system", icon: ActivityIcon }],
  },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <StethoscopeIcon className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">Open ICD Coder</span>
                <span className="truncate text-xs text-muted-foreground">ICD-10-CM prototype</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {NAV.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const active = item.match ? item.match(pathname) : pathname.startsWith(item.href)
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton isActive={active} tooltip={item.title} render={<Link href={item.href} />}>
                        <item.icon />
                        <span>{item.title}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <p className="px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
          Prototype — synthetic notes only
        </p>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
