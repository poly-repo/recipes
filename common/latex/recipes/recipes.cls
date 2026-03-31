\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{recipe_card}[2026/02/22 Recipe Card Class]

% Handle Paper Sizes
\DeclareOption{4x6}{\PassOptionsToPackage{paperwidth=6in, paperheight=4in}{geometry}}
\DeclareOption{A6}{\PassOptionsToPackage{paperwidth=148mm, paperheight=105mm}{geometry}}
\DeclareOption{halfletter}{\PassOptionsToPackage{paperwidth=8.5in, paperheight=5.5in}{geometry}}
\ExecuteOptions{4x6}
\ProcessOptions\relax

\LoadClass[9pt]{article}
\RequirePackage[margin=0.3in]{geometry}
\RequirePackage{fontspec}
\RequirePackage{fontawesome5} % For icons
\RequirePackage{graphicx}
\RequirePackage{qrcode}       % For the web link
\RequirePackage{xparse}
\RequirePackage{multicol}
\RequirePackage{xcolor}
\RequirePackage{eso-pic}
\RequirePackage{tabularx}
\RequirePackage[most]{tcolorbox}

\definecolor{recipeRed}{HTML}{A51C30} % Matches your sample's dark red

% Command for the header icons
\newcommand{\recipeMetadata}[6]{
    \centering
    \small
    \faUtensils\ #1 \quad 
    \faHourglassHalf\ #2 \quad 
    \faFire\ #3 \quad 
    \faHistory\ #4 \quad 
    \faUsers\ #5 \quad 
    \faBook\ #6
    \par\medskip
}

% Recipe environment for multi-recipe documents.
% Usage:
%   \begin{recipe}[<optional right-side header content>]{<title>}
%     ...one full recipe...
%   \end{recipe}
% Each recipe starts on a fresh page, except the first one.
\newcounter{recipeCardIndex}
\NewDocumentEnvironment{recipe}{ O{} m }{
    \ifnum\value{recipeCardIndex}>0\clearpage\fi
    \stepcounter{recipeCardIndex}
    \pagestyle{empty}
    \noindent\recipeTitle{#2}%
    \if\relax\detokenize{#1}\relax\else\hfill #1\fi
    \recipeTitleDivider
}{
    \par
}

% Base spirit marker mapping (top-to-bottom segments on right page edge):
%   1 Gin     -> #3AA17E
%   2 Whiskey -> #B06A2B
%   3 Rum     -> #7A4A2C
%   4 Vodka   -> #5FA8D3
%   5 Tequila -> #C9A227
\definecolor{spiritGin}{HTML}{3AA17E}
\definecolor{spiritWhiskey}{HTML}{B06A2B}
\definecolor{spiritRum}{HTML}{7A4A2C}
\definecolor{spiritVodka}{HTML}{5FA8D3}
\definecolor{spiritTequila}{HTML}{C9A227}
\newlength{\spiritStripWidth}
\newlength{\spiritStripInset}
\newlength{\spiritSegmentHeight}
\setlength{\spiritStripWidth}{0.12in}
\setlength{\spiritStripInset}{0.02in}
\setlength{\spiritSegmentHeight}{0.2\paperheight}
\newcommand{\setBaseSpirit}[1]{%
    \gdef\recipeSpiritArg{#1}%
        \gdef\recipeSpiritSegmentIndex{0}%
    \gdef\recipeSpiritWhiskey{Whiskey}%
    \gdef\recipeSpiritRum{Rum}%
    \gdef\recipeSpiritVodka{Vodka}%
    \gdef\recipeSpiritTequila{Tequila}%
    \ifx\recipeSpiritArg\recipeSpiritWhiskey
        \gdef\recipeSpiritSegmentIndex{1}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritRum
        \gdef\recipeSpiritSegmentIndex{2}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritVodka
        \gdef\recipeSpiritSegmentIndex{3}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritTequila
        \gdef\recipeSpiritSegmentIndex{4}%
    \fi
    \AddToShipoutPictureFG*{%
        \AtPageUpperLeft{%
            \begin{tikzpicture}[overlay]
                \pgfmathsetlengthmacro{\spiritX}{\paperwidth-\spiritStripInset-\spiritStripWidth}
                \draw[draw=black!25,line width=0.2pt] (\spiritX,0) rectangle ++(\spiritStripWidth,-\paperheight);
                \foreach \i in {1,2,3,4}{
                    \draw[draw=black!25,line width=0.2pt] (\spiritX,-\i*\spiritSegmentHeight) -- ++(\spiritStripWidth,0);
                }
                \ifnum\recipeSpiritSegmentIndex=0 \fill[spiritGin] (\spiritX,0) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
                \ifnum\recipeSpiritSegmentIndex=1 \fill[spiritWhiskey] (\spiritX,-\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
                \ifnum\recipeSpiritSegmentIndex=2 \fill[spiritRum] (\spiritX,-2\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
                \ifnum\recipeSpiritSegmentIndex=3 \fill[spiritVodka] (\spiritX,-3\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
                \ifnum\recipeSpiritSegmentIndex=4 \fill[spiritTequila] (\spiritX,-4\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
            \end{tikzpicture}%
        }%
    }%
}

\newcommand{\cocktailHistory}[1]{
    \clearpage
    \begin{center}
        \large\textbf{\color{recipeRed} The History \& Provenance}
    \end{center}
    \small #1
  }



\definecolor{recipeRed}{HTML}{A51C30}
% Define fonts by their system names.
\setmainfont{Inter}
\setmonofont{JetBrains Mono}
\newfontfamily\sketchfont{Fredericka the Great}

\newcommand{\recipeTitle}[1]{{\color[HTML]{A51C30} \Huge \sketchfont
      #1}}}
\newcommand{\recipeTitleDivider}{\par\vspace{2pt}\noindent\rule{\textwidth}{0.4pt}\par\vspace{2pt}}

% The Footer Box with the L-bracket
\newtcolorbox{recipeinfo}{
    enhanced,
    sharp corners,
    boxrule=0pt,
    colback=white,
    borderline west={1pt}{0pt}{recipeRed},
    borderline south={1pt}{0pt}{recipeRed},
    left=10pt,
    bottom=5pt,
    top=5pt,
    fontupper=\itshape\small,
    width=0.85\textwidth
}  

% Food Metadata: Prep, Cook, Temp/Time, Rest, Servings, Difficulty
\newcommand{\foodMeta}[6]{
    \small \faUtensils\ #1 \quad \faClock\ #2 \quad \faFire\ #3 \quad \faSnowflake\ #4 \quad \faUsers\ #5 \quad \faLayerGroup\ #6
}

% Cocktail icon mapping (all currently available assets)
% Glassware:
%   Champagne Flute -> champagne-flute.png
%   Collins / Collins Glass -> collins-glass.png
%   Coupe / Coupe Glass -> coupe-glass.png
%   Highball / Highball Glass -> highball-glass.png
%   Hurricane / Hurricane Glass -> hurricane-glass.png
%   Martini / Martini Glass -> martini-glass.png
%   Nick and Nora / Nick & Nora / Nick and Nora Glass -> nick-and-nora-glass.png
%   Rocks / Rock Glass / Old Fashioned -> rock-glass.png
%   Tiki Mug / Tiki -> tiki-mug.png
%   Wine / Wine Glass -> wine-glass.png
%
% Methods:
%   Blend / Blended -> blend.png
%   Build / Built -> build.png
%   Flame / Flamed -> flame.png
%   Float / Floated -> float.png
%   Layer / Layered -> layer.png
%   Muddle / Muddled -> muddle.png
%   Reverse Dry Shake -> reverse-dry-shake.png
%   Shake / Shaken -> shake.png
%   Stir / Stirred -> stirr.png
%
% Normalization:
%   - Case-insensitive
%   - Hyphen and space tolerant
%   - Ampersand-friendly aliases where practical

\ExplSyntaxOn
\prop_new:N \g_cocktail_glass_map_prop
\prop_new:N \g_cocktail_method_map_prop

\prop_gput:Nnn \g_cocktail_glass_map_prop {champagneflute} {champagne-flute.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {collins} {collins-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {collinsglass} {collins-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {coupe} {coupe-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {coupeglass} {coupe-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {highball} {highball-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {highballglass} {highball-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {hurricane} {hurricane-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {hurricaneglass} {hurricane-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {martini} {martini-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {martiniglass} {martini-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {nickandnora} {nick-and-nora-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {nickandnoraglass} {nick-and-nora-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {rocks} {rock-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {rockglass} {rock-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {oldfashioned} {rock-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {tikimug} {tiki-mug.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {tiki} {tiki-mug.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {wine} {wine-glass.png}
\prop_gput:Nnn \g_cocktail_glass_map_prop {wineglass} {wine-glass.png}

\prop_gput:Nnn \g_cocktail_method_map_prop {blend} {blend.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {blended} {blend.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {build} {build.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {built} {build.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {flame} {flame.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {flamed} {flame.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {float} {float.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {floated} {float.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {layer} {layer.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {layered} {layer.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {muddle} {muddle.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {muddled} {muddle.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {reversedryshake} {reverse-dry-shake.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {shake} {shake.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {shaken} {shake.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {stir} {stirr.png}
\prop_gput:Nnn \g_cocktail_method_map_prop {stirred} {stirr.png}

\cs_new_protected:Npn \cocktail_glass_file_for:nN #1#2
{
    \tl_set:Nn \l_tmpa_tl {#1}
    \tl_set:Nx \l_tmpa_tl { \tl_lower_case:n { \l_tmpa_tl } }
    \tl_replace_all:Nnn \l_tmpa_tl { \& } { and }
    \tl_remove_all:Nn \l_tmpa_tl { ~ }
    \tl_remove_all:Nn \l_tmpa_tl { - }
    \prop_get:NVNTF \g_cocktail_glass_map_prop \l_tmpa_tl #2 { } { \tl_clear:N #2 }
}

\cs_new_protected:Npn \cocktail_method_file_for:nN #1#2
{
    \tl_set:Nn \l_tmpa_tl {#1}
    \tl_set:Nx \l_tmpa_tl { \tl_lower_case:n { \l_tmpa_tl } }
    \tl_replace_all:Nnn \l_tmpa_tl { \& } { and }
    \tl_remove_all:Nn \l_tmpa_tl { ~ }
    \tl_remove_all:Nn \l_tmpa_tl { - }
    \prop_get:NVNTF \g_cocktail_method_map_prop \l_tmpa_tl #2 { } { \tl_clear:N #2 }
}

\cs_new_protected:Npn \cocktail_include_icon:nn #1#2
{
    \IfFileExists{assets/images/cocktails/#1/#2}
        {\includegraphics[height=1.35em]{assets/images/cocktails/#1/#2}}
        {
            \IfFileExists{../../../assets/images/cocktails/#1/#2}
                {\includegraphics[height=1.35em]{../../../assets/images/cocktails/#1/#2}}
                {}
        }
}

\cs_new_protected:Npn \cocktailGlassWithLabel #1
{
    \cocktail_glass_file_for:nN {#1} \l_tmpa_tl
    \tl_if_blank:VTF \l_tmpa_tl
        { #1 }
        {
            \raisebox{-0.15em}{
                \IfFileExists{assets/images/cocktails/glassware/\tl_use:N \l_tmpa_tl}
                    {\includegraphics[height=2.025em]{assets/images/cocktails/glassware/\tl_use:N \l_tmpa_tl}}
                    {
                        \IfFileExists{../../../assets/images/cocktails/glassware/\tl_use:N \l_tmpa_tl}
                            {\includegraphics[height=2.025em]{../../../assets/images/cocktails/glassware/\tl_use:N \l_tmpa_tl}}
                            {}
                    }
            }
        }
}

\cs_new_protected:Npn \cocktailMethodWithLabel #1
{
    \cocktail_method_file_for:nN {#1} \l_tmpa_tl
    \tl_if_blank:VTF \l_tmpa_tl
        { #1 }
        {
            \raisebox{-0.15em}{
                \IfFileExists{assets/images/cocktails/methods/\tl_use:N \l_tmpa_tl}
                    {\includegraphics[height=2.7em]{assets/images/cocktails/methods/\tl_use:N \l_tmpa_tl}}
                    {
                        \IfFileExists{../../../assets/images/cocktails/methods/\tl_use:N \l_tmpa_tl}
                            {\includegraphics[height=2.7em]{../../../assets/images/cocktails/methods/\tl_use:N \l_tmpa_tl}}
                            {}
                    }
            }
        }
}
\ExplSyntaxOff

% Cocktail Metadata: Glass, Method, Ice, Strength, Garnish
\newcommand{\cocktailMeta}[5]{
    \small \cocktailGlassWithLabel{#1} \quad \cocktailMethodWithLabel{#2} \quad #3 \quad #4 \quad #5\par
}

% Separate list environments for ingredients and process.
% These are intentionally independent (no forced row alignment).
\newenvironment{ingredients}{
    \vspace{8pt}
    \noindent\begin{minipage}[t]{0.48\textwidth}
    \textbf{Ingredients}\par
    \small
    \begin{itemize}
    \setlength{\itemsep}{1pt}
    \setlength{\parskip}{0pt}
    \setlength{\topsep}{2pt}
}{
    \end{itemize}
    \end{minipage}\hfill
}
\newcommand{\ingredient}[1]{\item #1}

\newenvironment{process}{
    \begin{minipage}[t]{0.48\textwidth}
    \textbf{Procedure}\par
    \small
    \renewcommand{\labelenumi}{{\color{recipeRed}\textbf{\arabic{enumi}}}}
    \begin{enumerate}
    \setlength{\itemsep}{1pt}
    \setlength{\parskip}{0pt}
    \setlength{\topsep}{2pt}
}{
    \end{enumerate}
    \end{minipage}\par
}
\newcommand{\step}[1]{\item #1}
