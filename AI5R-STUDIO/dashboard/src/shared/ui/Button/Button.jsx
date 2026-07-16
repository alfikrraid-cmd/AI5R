import clsx from "clsx";

export default function Button({
  children,
  variant = "primary",
  size = "md",
  type = "button",
  disabled = false,
  loading = false,
  fullWidth = false,
  leftIcon = null,
  rightIcon = null,
  className = "",
  onClick,
}) {
  const variants = {
    primary:
      "bg-emerald-500 hover:bg-emerald-600 text-white border border-emerald-500",

    secondary:
      "bg-slate-800 hover:bg-slate-700 text-white border border-slate-700",

    ghost:
      "bg-transparent hover:bg-slate-800 text-slate-200 border border-transparent",

    danger:
      "bg-red-500 hover:bg-red-600 text-white border border-red-500",
  };

  const sizes = {
    sm: "h-9 px-4 text-sm",
    md: "h-11 px-5 text-sm",
    lg: "h-14 px-7 text-base",
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={clsx(
        "inline-flex items-center justify-center gap-2",
        "rounded-2xl",
        "font-medium",
        "transition-all duration-200",
        "active:scale-95",
        "disabled:opacity-50",
        "disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        fullWidth && "w-full",
        className
      )}
    >
      {leftIcon}

      {loading ? "Loading..." : children}

      {rightIcon}
    </button>
  );
}