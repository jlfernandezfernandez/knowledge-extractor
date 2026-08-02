import { NavLink, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, HistoryIcon, LogOutIcon, UsersRoundIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import type { AuthenticatedUser } from "@/features/auth/types";

const navigation = [
  { to: "/", key: "home", icon: BookOpenIcon },
  { to: "/interviews", key: "interviews", icon: UsersRoundIcon },
  { to: "/history", key: "history", icon: HistoryIcon },
] as const;

const initials = (name: string) => name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();

function AccountMenu({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon" aria-label={t("shell.accountMenu")} />}>
        <Avatar size="sm">
          <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {/* DropdownMenuLabel is Base UI's MenuGroupLabel: it throws outside a Group. */}
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            {/* Item size="xs" self-zeroes its padding inside a dropdown. */}
            <Item size="xs">
              <ItemContent>
                <ItemTitle>{user.display_name}</ItemTitle>
                <ItemDescription>{user.email}</ItemDescription>
              </ItemContent>
            </Item>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onLogout}>
          <LogOutIcon aria-hidden="true" />
          {t("shell.signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Header markup lifted from the official sidebar-16 site header. */
export function SiteHeader({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  return (
    <header className="sticky top-0 z-50 flex w-full items-center border-b bg-background">
      {/* Same max-width and padding as every page, so the brand lines up with page titles. */}
      <div className="mx-auto flex h-14 w-full max-w-3xl items-center gap-2 px-4">
        {/* nativeButton={false}: this Button renders react-router's <a>, not a <button>. */}
        <Button variant="ghost" nativeButton={false} render={<NavLink to="/" aria-label={t("app.name")} />}>
          <span aria-hidden="true">🦉</span>
          <span className="hidden sm:inline">{t("app.name")}</span>
        </Button>
        <NavigationMenu aria-label={t("shell.primaryNavigation")}>
          <NavigationMenuList>
            {navigation.map(({ to, key, icon: Icon }) => (
              <NavigationMenuItem key={to}>
                <NavigationMenuLink
                  render={<NavLink to={to} end={to === "/"} />}
                  className={navigationMenuTriggerStyle()}
                  data-active={to === "/" ? pathname === "/" : pathname.startsWith(to)}
                >
                  <Icon aria-hidden="true" />
                  {/* Label stays in the accessibility tree at every width; only its pixels hide. */}
                  <span className="sr-only sm:not-sr-only">{t(`nav.${key}`)}</span>
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
          </NavigationMenuList>
        </NavigationMenu>
        <div className="grow" />
        <AccountMenu user={user} onLogout={onLogout} />
      </div>
    </header>
  );
}
