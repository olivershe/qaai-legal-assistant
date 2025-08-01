/**
 * Design Profile Service - Runtime loading of design tokens from examples/design/*.json
 * 
 * Maps tokens to CSS variables following examples/design/README.md patterns.
 * Single source of truth: examples/design/*.profile.json files.
 */

export interface DesignProfile {
  meta: {
    title: string;
    purpose: string;
    observed_on: string;
  };
  colors: {
    semantic: {
      bg: {
        default: string;
        canvas: string;
        subtle: string;
        sidebar: string;
        card: string;
        input: string;
        tab: {
          selected: string;
          hover: string;
        };
        dropzone: string;
        badge: string;
      };
      border: {
        default: string;
        muted: string;
        focus: string;
      };
      text: {
        primary: string;
        secondary: string;
        muted: string;
        inverse: string;
        placeholder: string;
        link: string;
      };
      icon: {
        primary: string;
        muted: string;
      };
      action: {
        primary: {
          bg: string;
          text: string;
          hoverBg: string;
          activeBg: string;
        };
      };
      focus: {
        ring: string;
      };
      shadow: {
        color: string;
      };
    };
  };
  typography: {
    font_family_stack: string[];
    scale: {
      display: { size: number; lineHeight: number; weight: number; tracking: number };
      h1: { size: number; lineHeight: number; weight: number; tracking: number };
      h2: { size: number; lineHeight: number; weight: number; tracking: number };
      body: { size: number; lineHeight: number; weight: number; tracking: number };
      label: { size: number; lineHeight: number; weight: number; tracking: number };
      caption: { size: number; lineHeight: number; weight: number; tracking: number };
    };
  };
  radii: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
    pill: number;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
  spacing: {
    unit: number;
    scale: number[];
  };
  layout: {
    app_shell: {
      sidebar: {
        width: number;
        paddingX: number;
        paddingY: number;
        borderRight: boolean;
      };
      topbar: {
        height: number;
        paddingX: number;
      };
      content: {
        maxWidth: number;
        paddingX: number;
        paddingY: number;
      };
    };
  };
  interaction: {
    timings_ms: {
      fast: number;
      base: number;
      slow: number;
    };
    easings: {
      standard: string;
    };
    focus_ring: string;
    hover_opacity: number;
    press_opacity: number;
  };
}

class DesignProfileService {
  private profiles: Map<string, DesignProfile> = new Map();
  private currentProfile: string = 'assistant';

  /**
   * Load a design profile from examples/design/*.profile.json
   */
  async loadProfile(profileName: string): Promise<DesignProfile> {
    if (this.profiles.has(profileName)) {
      return this.profiles.get(profileName)!;
    }

    try {
      // Load from examples/design directory (relative to project root)
      const response = await fetch(`../../examples/design/${profileName}.profile.json`);
      if (!response.ok) {
        throw new Error(`Failed to load profile: ${profileName}`);
      }
      
      const profile = await response.json() as DesignProfile;
      this.profiles.set(profileName, profile);
      return profile;
    } catch (error) {
      console.error(`Error loading design profile ${profileName}:`, error);
      throw error;
    }
  }

  /**
   * Apply design tokens to CSS variables
   * Maps core tokens following examples/design/README.md recommendations
   */
  async applyDesignVariables(profileName: string = 'assistant'): Promise<void> {
    const profile = await this.loadProfile(profileName);
    const root = document.documentElement;

    // Helper to set CSS custom property
    const setVar = (key: string, value: string) => {
      root.style.setProperty(key, value);
    };

    // Color tokens - semantic colors
    const colors = profile.colors.semantic;
    setVar('--bg-canvas', colors.bg.canvas);
    setVar('--bg-card', colors.bg.card);
    setVar('--bg-subtle', colors.bg.subtle);
    setVar('--bg-sidebar', colors.bg.sidebar);
    setVar('--bg-input', colors.bg.input);
    setVar('--bg-tab-selected', colors.bg.tab.selected);
    setVar('--bg-tab-hover', colors.bg.tab.hover);
    setVar('--bg-dropzone', colors.bg.dropzone);
    setVar('--bg-badge', colors.bg.badge);

    setVar('--border', colors.border.default);
    setVar('--border-muted', colors.border.muted);
    setVar('--border-focus', colors.border.focus);

    setVar('--text', colors.text.primary);
    setVar('--text-2', colors.text.secondary);
    setVar('--text-muted', colors.text.muted);
    setVar('--text-inverse', colors.text.inverse);
    setVar('--text-placeholder', colors.text.placeholder);
    setVar('--text-link', colors.text.link);

    setVar('--icon-primary', colors.icon.primary);
    setVar('--icon-muted', colors.icon.muted);

    setVar('--btn-bg', colors.action.primary.bg);
    setVar('--btn-text', colors.action.primary.text);
    setVar('--btn-hover-bg', colors.action.primary.hoverBg);
    setVar('--btn-active-bg', colors.action.primary.activeBg);

    setVar('--focus-ring', colors.focus.ring);
    setVar('--shadow-color', colors.shadow.color);

    // Radii tokens
    setVar('--radius-xs', `${profile.radii.xs}px`);
    setVar('--radius-sm', `${profile.radii.sm}px`);
    setVar('--radius-md', `${profile.radii.md}px`);
    setVar('--radius-lg', `${profile.radii.lg}px`);
    setVar('--radius-xl', `${profile.radii.xl}px`);
    setVar('--radius-pill', `${profile.radii.pill}px`);

    // Typography tokens
    const typography = profile.typography.scale;
    setVar('--font-size-display', `${typography.display.size}px`);
    setVar('--font-size-h1', `${typography.h1.size}px`);
    setVar('--font-size-h2', `${typography.h2.size}px`);
    setVar('--font-size-body', `${typography.body.size}px`);
    setVar('--font-size-label', `${typography.label.size}px`);
    setVar('--font-size-caption', `${typography.caption.size}px`);

    setVar('--line-height-display', `${typography.display.lineHeight}px`);
    setVar('--line-height-h1', `${typography.h1.lineHeight}px`);
    setVar('--line-height-h2', `${typography.h2.lineHeight}px`);
    setVar('--line-height-body', `${typography.body.lineHeight}px`);
    setVar('--line-height-label', `${typography.label.lineHeight}px`);
    setVar('--line-height-caption', `${typography.caption.lineHeight}px`);

    // Font family
    setVar('--font-family', profile.typography.font_family_stack.join(', '));

    // Shadows
    setVar('--shadow-sm', profile.shadows.sm);
    setVar('--shadow-md', profile.shadows.md);
    setVar('--shadow-lg', profile.shadows.lg);

    // Layout tokens
    setVar('--sidebar-width', `${profile.layout.app_shell.sidebar.width}px`);
    setVar('--content-max-width', `${profile.layout.app_shell.content.maxWidth}px`);
    setVar('--topbar-height', `${profile.layout.app_shell.topbar.height}px`);

    // Interaction tokens
    setVar('--timing-fast', `${profile.interaction.timings_ms.fast}ms`);
    setVar('--timing-base', `${profile.interaction.timings_ms.base}ms`);
    setVar('--timing-slow', `${profile.interaction.timings_ms.slow}ms`);
    setVar('--easing-standard', profile.interaction.easings.standard);

    // For Tailwind CSS compatibility - map to standard design system tokens
    setVar('--background', colors.bg.canvas);
    setVar('--foreground', colors.text.primary);
    setVar('--card', colors.bg.card);
    setVar('--card-foreground', colors.text.primary);
    setVar('--popover', colors.bg.card);
    setVar('--popover-foreground', colors.text.primary);
    setVar('--primary', colors.action.primary.bg);
    setVar('--primary-foreground', colors.action.primary.text);
    setVar('--secondary', colors.bg.subtle);
    setVar('--secondary-foreground', colors.text.secondary);
    setVar('--muted', colors.bg.subtle);
    setVar('--muted-foreground', colors.text.muted);
    setVar('--accent', colors.bg.tab.selected);
    setVar('--accent-foreground', colors.text.primary);
    setVar('--destructive', '#ef4444');
    setVar('--destructive-foreground', colors.text.inverse);
    setVar('--input', colors.bg.input);
    setVar('--ring', colors.focus.ring);

    this.currentProfile = profileName;
  }

  /**
   * Get current profile name
   */
  getCurrentProfile(): string {
    return this.currentProfile;
  }

  /**
   * Get loaded profile by name
   */
  getProfile(profileName: string): DesignProfile | undefined {
    return this.profiles.get(profileName);
  }

  /**
   * Get all available profile names
   */
  getAvailableProfiles(): string[] {
    return ['assistant', 'vault', 'workflow.draft-from-template'];
  }
}

export const designProfileService = new DesignProfileService();