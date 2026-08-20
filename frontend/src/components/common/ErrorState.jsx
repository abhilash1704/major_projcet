import { cn } from "../../utils/cn";

export const ErrorState = ({ title = "Something went wrong", description, action }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-red-50 rounded-xl border border-red-100">
      <div className="text-danger mb-4 text-4xl">!</div>
      <h3 className="text-lg font-semibold text-danger mb-2">{title}</h3>
      <p className="text-sm text-red-600 max-w-md mb-6">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
