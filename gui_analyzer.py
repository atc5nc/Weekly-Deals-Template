import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import json
import os

from deal_analyzer_enhanced import DealAnalyzer, build_weekly_email_html


class EnhancedDealAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏆 Grocery Deal Analyzer - Multi-Retailer")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f5f5f5")

        # Current loaded deals
        self.all_deals = []
        self.current_filename = ""

        # Header Frame
        self.create_header()

        # Control Panel
        self.create_control_panel()

        # Results area
        self.create_results_area()

        # Status bar
        self.create_status_bar()

    def create_header(self):
        """Create header section"""
        header_frame = tk.Frame(self.root, bg="#4CAF50", height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title = tk.Label(
            header_frame,
            text="🏆 Grocery Deal Analyzer",
            font=("Arial", 24, "bold"),
            bg="#4CAF50",
            fg="white"
        )
        title.pack(pady=15)

        subtitle = tk.Label(
            header_frame,
            text="HEB • Smart & Final • Sprouts • Amazon Fresh • Whole Foods",
            font=("Arial", 10),
            bg="#4CAF50",
            fg="#e8f5e9"
        )
        subtitle.pack()

    def create_control_panel(self):
        """Create control panel with options"""
        control_frame = tk.Frame(self.root, bg="#f5f5f5")
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        # Left side - Upload button
        left_frame = tk.Frame(control_frame, bg="#f5f5f5")
        left_frame.pack(side=tk.LEFT, padx=10)

        self.upload_btn = tk.Button(
            left_frame,
            text="📁 Upload JSON File",
            command=self.upload_file,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10,
            cursor="hand2",
            relief=tk.RAISED
        )
        self.upload_btn.pack(side=tk.LEFT, padx=5)

        # File info label
        self.file_label = tk.Label(
            left_frame,
            text="No file loaded",
            font=("Arial", 10),
            bg="#f5f5f5",
            fg="#666"
        )
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Right side - Options
        right_frame = tk.Frame(control_frame, bg="#f5f5f5")
        right_frame.pack(side=tk.RIGHT, padx=10)

        # Number of deals selector
        tk.Label(
            right_frame,
            text="Show top:",
            font=("Arial", 10),
            bg="#f5f5f5"
        ).pack(side=tk.LEFT, padx=5)

        self.top_n_var = tk.StringVar(value="6")
        top_n_dropdown = ttk.Combobox(
            right_frame,
            textvariable=self.top_n_var,
            values=["3", "6", "10", "12", "15", "20"],
            width=5,
            state="readonly"
        )
        top_n_dropdown.pack(side=tk.LEFT, padx=5)

        # Retailer filter
        tk.Label(
            right_frame,
            text="Retailer:",
            font=("Arial", 10),
            bg="#f5f5f5"
        ).pack(side=tk.LEFT, padx=(20, 5))

        self.retailer_var = tk.StringVar(value="All")
        self.retailer_dropdown = ttk.Combobox(
            right_frame,
            textvariable=self.retailer_var,
            values=["All"],
            width=15,
            state="readonly"
        )
        self.retailer_dropdown.pack(side=tk.LEFT, padx=5)

        # Show details checkbox
        self.show_details_var = tk.BooleanVar(value=True)
        details_check = tk.Checkbutton(
            right_frame,
            text="Show scoring details",
            variable=self.show_details_var,
            font=("Arial", 10),
            bg="#f5f5f5"
        )
        details_check.pack(side=tk.LEFT, padx=(20, 5))

        # Analyze button
        self.analyze_btn = tk.Button(
            right_frame,
            text="⚡ Analyze",
            command=self.analyze_deals,
            font=("Arial", 11, "bold"),
            bg="#2196F3",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=10)

        # NEW: Generate Email button
        self.email_btn = tk.Button(
            right_frame,
            text="📧 Generate Email",
            command=self.generate_email,
            font=("Arial", 11, "bold"),
            bg="#9C27B0",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.email_btn.pack(side=tk.LEFT, padx=10)

        # Optional: auto-generate email after Analyze
        self.auto_email_var = tk.BooleanVar(value=False)
        auto_email_check = tk.Checkbutton(
            right_frame,
            text="Auto-email",
            variable=self.auto_email_var,
            font=("Arial", 10),
            bg="#f5f5f5"
        )
        auto_email_check.pack(side=tk.LEFT, padx=(10, 0))

    def create_results_area(self):
        """Create results display area"""
        results_frame = tk.Frame(self.root, bg="#f5f5f5")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        results_label = tk.Label(
            results_frame,
            text="📊 Analysis Results",
            font=("Arial", 12, "bold"),
            bg="#f5f5f5"
        )
        results_label.pack(anchor=tk.W, pady=(0, 5))

        text_frame = tk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_text = tk.Text(
            text_frame,
            width=90,
            height=25,
            font=("Courier", 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            bg="white",
            relief=tk.SOLID,
            borderwidth=1
        )
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_text.yview)

        button_frame = tk.Frame(results_frame, bg="#f5f5f5")
        button_frame.pack(fill=tk.X, pady=(10, 0))

        save_btn = tk.Button(
            button_frame,
            text="💾 Save Results",
            command=self.save_results,
            font=("Arial", 10),
            bg="#607D8B",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2"
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        clear_btn = tk.Button(
            button_frame,
            text="🗑️ Clear",
            command=self.clear_results,
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2"
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

    def create_status_bar(self):
        """Create status bar"""
        self.status = tk.Label(
            self.root,
            text="Ready to analyze deals",
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#e0e0e0",
            font=("Arial", 9)
        )
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def upload_file(self):
        """Handle file upload"""
        filename = filedialog.askopenfilename(
            title="Select JSON file with deals",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.status.config(text=f"Loading {filename}...")
                self.root.update()

                with open(filename, "r", encoding="utf-8") as f:
                    self.all_deals = json.load(f)

                self.current_filename = filename

                deal_count = len(self.all_deals)
                retailers = list(set([d.get("retailer", "Unknown") for d in self.all_deals]))

                self.file_label.config(
                    text=f"✅ {deal_count} deals loaded",
                    fg="#2E7D32"
                )

                retailer_options = ["All"] + sorted(retailers)
                self.retailer_dropdown["values"] = retailer_options

                self.analyze_btn.config(state=tk.NORMAL)
                self.email_btn.config(state=tk.NORMAL)

                self.status.config(
                    text=f"✅ Loaded {deal_count} deals from {len(retailers)} retailer(s): {', '.join(retailers)}"
                )

                self.analyze_deals()

            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON file!")
                self.status.config(text="❌ Invalid JSON file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                self.status.config(text=f"❌ Error: {str(e)}")

    def analyze_deals(self):
        """Analyze loaded deals"""
        if not self.all_deals:
            messagebox.showwarning("Warning", "Please upload a JSON file first!")
            return

        try:
            self.status.config(text="🔍 Analyzing deals...")
            self.root.update()

            top_n = int(self.top_n_var.get())
            retailer_filter = None if self.retailer_var.get() == "All" else self.retailer_var.get()
            show_details = self.show_details_var.get()

            analyzer = DealAnalyzer(retailer_filter=retailer_filter)
            top_deals = analyzer.analyze_deals(self.all_deals, top_n=top_n)

            if not top_deals:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, "❌ No deals found matching criteria\n\n")
                self.results_text.insert(tk.END, "Try:\n")
                self.results_text.insert(tk.END, "• Changing the retailer filter\n")
                self.results_text.insert(tk.END, "• Checking if deals have prices\n")
                self.results_text.insert(tk.END, "• Verifying the JSON format\n")
                self.status.config(text="❌ No deals found")
                return

            output = analyzer.format_output(top_deals, show_details=show_details)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, output)

            avg_score = sum(d["engagement_score"] for d in top_deals) / len(top_deals)
            if retailer_filter is None:
                self.status.config(
                    text=f"✅ Analyzed {len(self.all_deals)} deals - Showing Top {len(top_deals)} (Avg Score: {avg_score:.1f})"
                )
            else:
                retailer = top_deals[0].get("retailer", "Unknown")
                self.status.config(
                    text=f"✅ Analyzed {len(self.all_deals)} deals - Top {len(top_deals)} from {retailer} (Avg Score: {avg_score:.1f})"
                )

            # Optional auto email generation
            if self.auto_email_var.get():
                self.generate_email()

        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
            self.status.config(text=f"❌ Error: {str(e)}")

    def generate_email(self):
        """
        Generate a filled HTML email using newsletter_3.html template.

        IMPORTANT:
        - Uses the GUI "Show top #" as the number of items PER RETAILER in the email.
        - Saves the final HTML wherever you choose in the save dialog.
        """
        if not self.all_deals:
            messagebox.showwarning("Warning", "Please upload a JSON file first!")
            return

        try:
            top_n = int(self.top_n_var.get())
            retailer_filter = None if self.retailer_var.get() == "All" else self.retailer_var.get()

            eligible_deals = self.all_deals
            if retailer_filter is not None:
                eligible_deals = [d for d in self.all_deals if d.get("retailer") == retailer_filter]

            if not eligible_deals:
                messagebox.showwarning("Warning", "No deals available for the selected retailer filter.")
                return

            # Prefer local newsletter_3.html automatically
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_template = os.path.join(base_dir, "newsletter_3.html")

            if os.path.exists(default_template):
                template_path = default_template
            else:
                template_path = filedialog.askopenfilename(
                    title="Select HTML email template (newsletter_3.html)",
                    filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
                )
                if not template_path:
                    return

            with open(template_path, "r", encoding="utf-8") as f:
                template_html = f.read()

            # Optional personalization
            display_name = simpledialog.askstring("Email Personalization", "Recipient first name (optional):") or "there"
            email = simpledialog.askstring("Email Personalization", "Recipient email (optional):") or ""
            zip_code = simpledialog.askstring("Email Personalization", "ZIP code (optional):") or ""
            week_of = simpledialog.askstring("Email Personalization", "Week of (optional, e.g., Jan 20):") or None

            self.status.config(text="📧 Generating email HTML...")
            self.root.update()

            html = build_weekly_email_html(
                all_deals=eligible_deals,
                template_html=template_html,
                top_n_per_retailer=top_n,
                display_name=display_name,
                email=email,
                zip_code=zip_code,
                week_of=week_of,
            )

            # Default output name in the same folder as the JSON file (or script folder)
            if self.current_filename:
                default_out_dir = os.path.dirname(self.current_filename)
            else:
                default_out_dir = base_dir

            default_out = os.path.join(default_out_dir, "prox_weekly_email.html")

            out_path = filedialog.asksaveasfilename(
                title="Save generated email HTML",
                initialdir=default_out_dir,
                initialfile=os.path.basename(default_out),
                defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
            )
            if not out_path:
                self.status.config(text="Email generation canceled")
                return

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)

            messagebox.showinfo("Success", f"✅ Email generated and saved:\n{out_path}")
            self.status.config(text=f"✅ Email saved: {out_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Email generation failed: {str(e)}")
            self.status.config(text=f"❌ Email error: {str(e)}")

    def save_results(self):
        """Save results to file"""
        if not self.results_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "No results to save!")
            return

        filename = filedialog.asksaveasfilename(
            title="Save results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.results_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Results saved to {filename}")
                self.status.config(text=f"✅ Saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def clear_results(self):
        """Clear results area"""
        self.results_text.delete(1.0, tk.END)
        self.status.config(text="Results cleared")


def main():
    root = tk.Tk()
    app = EnhancedDealAnalyzerGUI(root)

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()
