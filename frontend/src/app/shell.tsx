import { NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, ChevronsUpDownIcon, HistoryIcon, LogOutIcon, MessageCircleQuestionIcon, UsersRoundIcon } from "lucide-react";
import { Brand } from "@/components/brand";
import { GitHubLogo } from "@/components/github-logo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { AuthenticatedUser } from "./router";

const navigation = [
  { to: "/", key: "home", icon: BookOpenIcon },
  { to: "/ask", key: "ask", icon: MessageCircleQuestionIcon },
  { to: "/interviews", key: "interviews", icon: UsersRoundIcon },
  { to: "/history", key: "history", icon: HistoryIcon },
] as const;

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function AppSidebar({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { isMobile, setOpenMobile } = useSidebar();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<NavLink to="/" aria-label={t("app.name")} onClick={() => setOpenMobile(false)} />}>
              <Brand label={t("app.name")} />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {navigation.map(({ to, key, icon: Icon }) => (
            <SidebarMenuItem key={to}>
              <SidebarMenuButton
                render={<NavLink to={to} end={to === "/"} onClick={() => setOpenMobile(false)} />}
                isActive={to === "/" ? pathname === "/" : pathname.startsWith(to)}
                tooltip={t(`nav.${key}`)}
              >
                <Icon aria-hidden="true" />
                <span>{t(`nav.${key}`)}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger render={<SidebarMenuButton size="lg" aria-label={t("shell.accountMenu")} tooltip={user.display_name} />}>
                <Avatar size="lg">
                  <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
                </Avatar>
                <span className="min-w-0 flex-1 text-left group-data-[collapsible=icon]:hidden">
                  <span className="block truncate text-sm font-medium">{user.display_name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{user.email}</span>
                </span>
                <ChevronsUpDownIcon aria-hidden="true" data-icon="inline-end" className="group-data-[collapsible=icon]:hidden" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" side={isMobile ? "bottom" : "right"} sideOffset={4}>
                <DropdownMenuGroup>
                  <DropdownMenuLabel>
                    <div className="flex flex-col gap-0.5">
                      <span>{user.display_name}</span>
                      <span className="font-normal">{user.email}</span>
                    </div>
                  </DropdownMenuLabel>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={onLogout}>
                    <LogOutIcon aria-hidden="true" />
                    {t("shell.signOut")}
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const activeNavItem = navigation.find((item) => item.to === "/" ? pathname === "/" : pathname.startsWith(item.to));
  const activeTitle = activeNavItem ? t(`nav.${activeNavItem.key}`) : null;

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar user={user} onLogout={onLogout} />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b px-4 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
            <div className="flex items-center gap-2">
              <SidebarTrigger aria-label={t("shell.openNavigation")} className="-ml-1" />
              <Separator orientation="vertical" className="mr-2 h-4" />
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem className="hidden md:block">
                    <BreadcrumbLink render={<NavLink to="/" />}>
                      {t("app.name")}
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  {activeTitle && (
                    <>
                      <BreadcrumbSeparator className="hidden md:block" />
                      <BreadcrumbItem>
                        <BreadcrumbPage>{activeTitle}</BreadcrumbPage>
                      </BreadcrumbItem>
                    </>
                  )}
                </BreadcrumbList>
              </Breadcrumb>
            </div>
            <div className="flex items-center gap-2">
              <a
                href="https://github.com/jlfernandezfernandez/knowli"
                aria-label={t("shell.repository")}
                rel="noreferrer"
                target="_blank"
                className={buttonVariants({ variant: "ghost", size: "icon" })}
              >
                <GitHubLogo aria-hidden="true" />
              </a>
            </div>
          </header>
          <Outlet />
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
