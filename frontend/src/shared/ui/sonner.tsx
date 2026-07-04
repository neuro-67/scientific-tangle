import { Toaster as SonnerToaster } from "sonner";

type Props = React.ComponentProps<typeof SonnerToaster>;

/** App-wide toast portal. Mount once near the app root. */
function Toaster(props: Props) {
  return (
    <SonnerToaster
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
