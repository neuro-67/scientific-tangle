import { Input } from "./input";

type Props = {
  icon: string;
  alt?: string;
} & React.ComponentProps<typeof Input>;

/** Input with a small icon inside the left side. */
export function IconInput({ icon, alt = "", className, ...props }: Props) {
  return (
    <div className="relative">
      <img
        src={icon}
        alt={alt}
        className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 object-contain opacity-70"
      />
      <Input className={`pl-10 ${className ?? ""}`} {...props} />
    </div>
  );
}
