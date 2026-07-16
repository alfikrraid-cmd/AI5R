import PropTypes from "prop-types";
import clsx from "clsx";

export default function Card({
  title,
  subtitle,
  footer,
  children,
  className = "",
  padding = "p-6",
}) {
  return (
    <div
      className={clsx(
        "rounded-3xl",
        "border border-slate-700",
        "bg-slate-900",
        "shadow-lg",
        "transition-all duration-200",
        "hover:border-emerald-500",
        "hover:shadow-emerald-500/10",
        padding,
        className
      )}
    >
      {(title || subtitle) && (
        <div className="mb-5">
          {title && (
            <h2 className="text-lg font-semibold text-white">
              {title}
            </h2>
          )}

          {subtitle && (
            <p className="mt-1 text-sm text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
      )}

      <div>{children}</div>

      {footer && (
        <div className="mt-6 border-t border-slate-800 pt-4 text-xs text-slate-500">
          {footer}
        </div>
      )}
    </div>
  );
}

Card.propTypes = {
  title: PropTypes.string,
  subtitle: PropTypes.string,
  footer: PropTypes.node,
  children: PropTypes.node,
  className: PropTypes.string,
  padding: PropTypes.string,
};