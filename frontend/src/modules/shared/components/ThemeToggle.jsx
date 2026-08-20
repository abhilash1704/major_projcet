import { Sun, Moon } from "lucide-react";
import { IconButton } from "./IconButton";
import { useState, useEffect } from "react";

export const ThemeToggle = () => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <IconButton 
      icon={isDark ? Sun : Moon} 
      onClick={() => setIsDark(!isDark)} 
      className={isDark ? "text-warning hover:text-warning" : ""}
    />
  );
};
