\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{recipe-card}[2026/02/22 Recipe Card Class]

% Handle Paper Sizes
\DeclareOption{4x6}{\PassOptionsToPackage{paperwidth=6in, paperheight=4in}{geometry}}
\DeclareOption{A6}{\PassOptionsToPackage{paperwidth=148mm, paperheight=105mm}{geometry}}
\DeclareOption{halfletter}{\PassOptionsToPackage{paperwidth=8.5in, paperheight=5.5in}{geometry}}
\newcommand{\recipeCardCategory}{cocktail}
\newcommand{\recipeCardCategoryCocktail}{cocktail}
\newcommand{\recipeCardCategoryFood}{food}
\DeclareOption{cocktail}{\renewcommand{\recipeCardCategory}{cocktail}}
\DeclareOption{food}{\renewcommand{\recipeCardCategory}{food}}
\ExecuteOptions{4x6,cocktail}
\ProcessOptions\relax

\LoadClass[10pt]{article}
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
\RequirePackage{etoolbox}
\RequirePackage{pgfpages}

\makeatletter
\def\ps@empty{%
    \let\@mkboth\@gobbletwo
    \let\@oddhead\@empty
    \let\@evenhead\@empty
    \let\@oddfoot\@empty
    \let\@evenfoot\@empty
}
\let\ps@plain\ps@empty
\makeatother

% Print-ready imposition: place up to four complete front/back recipe strips on
% one US Letter sheet. Each recipe contributes two logical pages: front, back.
\pgfpagesdeclarelayout{letter-recipe-strips}
{
    \edef\pgfpageoptionborder{0pt}
}
{
    \pgfpagesphysicalpageoptions{
        logical pages=8,
        physical width=8.5in,
        physical height=11in,
    }
    \pgfpageslogicalpageoptions{1}{
        center=\pgfpoint{2.5in}{9.5in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{2}{
        center=\pgfpoint{6.5in}{9.5in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{3}{
        center=\pgfpoint{2.5in}{7.0in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{4}{
        center=\pgfpoint{6.5in}{7.0in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{5}{
        center=\pgfpoint{2.5in}{4.5in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{6}{
        center=\pgfpoint{6.5in}{4.5in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{7}{
        center=\pgfpoint{2.5in}{2.0in},
        xscale=0.6666667,
        yscale=0.625,
    }
    \pgfpageslogicalpageoptions{8}{
        center=\pgfpoint{6.5in}{2.0in},
        xscale=0.6666667,
        yscale=0.625,
    }
}
\pgfpagesuselayout{letter-recipe-strips}

% pgfpages passes a legacy second argument to \pgftransformxscale. With this
% LuaLaTeX/PGF combination that argument leaks as material in the shipout loop,
% so drop it instead of hiding it.
\makeatletter
\patchcmd{\pgfpages@buildshipoutbox}
    {\pgftransformxscale{\csname pgfpages@p@\the\pgf@cpn @xscale\endcsname}{1}}
    {\pgftransformxscale{\csname pgfpages@p@\the\pgf@cpn @xscale\endcsname}}
    {}
    {}
\makeatother

\AtBeginDocument{%
    \pagestyle{empty}%
    \pagenumbering{gobble}%
    \renewcommand{\thepage}{}%
}

\newcommand{\frontCardMargins}{%
    \setlength{\oddsidemargin}{-0.7in}%
    \setlength{\evensidemargin}{-0.7in}%
    \setlength{\textwidth}{4.95in}%
    \setlength{\hsize}{\textwidth}%
    \setlength{\columnwidth}{\textwidth}%
    \setlength{\linewidth}{\textwidth}%
}

\newcommand{\backCardMargins}{%
    \setlength{\oddsidemargin}{-0.25in}%
    \setlength{\evensidemargin}{-0.25in}%
    \setlength{\textwidth}{4.95in}%
    \setlength{\hsize}{\textwidth}%
    \setlength{\columnwidth}{\textwidth}%
    \setlength{\linewidth}{\textwidth}%
}

\newcommand{\back}{%
    \newpage
    \backCardMargins
    \thispagestyle{empty}%
}

\newcommand{\drawRecipeTopCutLine}{%
    \AddToShipoutPictureFG*{%
        \AtPageUpperLeft{%
            \begin{tikzpicture}[overlay]
                \draw[draw=black!50,line width=0.2pt,dash pattern=on 0.35pt off 1.7pt]
                    (-0.75in,0) -- (12in,0);
            \end{tikzpicture}%
        }%
    }%
}

\newcommand{\drawRecipeBottomCutLine}{%
    \AddToShipoutPictureFG*{%
        \AtPageUpperLeft{%
            \begin{tikzpicture}[overlay]
                \draw[draw=black!50,line width=0.2pt,dash pattern=on 0.35pt off 1.7pt]
                    (-6.75in,-\paperheight) -- (6in,-\paperheight);
            \end{tikzpicture}%
        }%
    }%
}

\newcommand{\drawRecipeTopCutLineIfNeeded}{%
    \pgfmathtruncatemacro{\recipeCutLineRemainder}{mod(\value{recipeCardIndex},4)}%
    \ifnum\recipeCutLineRemainder=0
        \drawRecipeTopCutLine
    \fi
}

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
\NewDocumentEnvironment{recipe}{ O{} m }{%
    \ifnum\value{recipeCardIndex}>0\clearpage\fi
    \drawRecipeTopCutLineIfNeeded
    \frontCardMargins
    \stepcounter{recipeCardIndex}%
    \pagestyle{empty}%
    \thispagestyle{empty}%
    \par\noindent\recipeTitle{#2}%
    \if\relax\detokenize{#1}\relax\else\hfill #1\fi
    \recipeTitleDivider
}{%
    \par
    \drawRecipeBottomCutLine
}

% Edge marker mapping.
% Cocktail mode (top-to-bottom):
%   1 Gin     -> #3AA17E
%   2 Whiskey -> #B06A2B
%   3 Rum     -> #7A4A2C
%   4 Vodka   -> #5FA8D3
%   5 Tequila -> #C9A227
% Food mode (top-to-bottom):
%   1 Bakery  -> #D18F3C
%   2 Primi   -> #4B9D7C
%   3 Secondi -> #A1533B
\definecolor{spiritGin}{HTML}{3AA17E}
\definecolor{spiritWhiskey}{HTML}{B06A2B}
\definecolor{spiritRum}{HTML}{7A4A2C}
\definecolor{spiritVodka}{HTML}{5FA8D3}
\definecolor{spiritTequila}{HTML}{C9A227}
\definecolor{recipeTypeBakery}{HTML}{D18F3C}
\definecolor{recipeTypePrimi}{HTML}{4B9D7C}
\definecolor{recipeTypeSecondi}{HTML}{A1533B}
\newlength{\spiritStripWidth}
\newlength{\spiritStripInset}
\newlength{\spiritSegmentHeight}
\setlength{\spiritStripWidth}{0.12in}
\setlength{\spiritStripInset}{0pt}
\setlength{\spiritSegmentHeight}{\dimexpr\paperheight/5\relax}
\newcommand{\recipeBarMode}{cocktail}
\newcommand{\recipeSpiritSegmentIndex}{0}
\newcommand{\recipeTypeSegmentIndex}{0}

\newcommand{\recipeBarUseCocktailDefaults}{%
    \gdef\recipeBarMode{cocktail}%
    \setlength{\spiritSegmentHeight}{\dimexpr\paperheight/5\relax}%
}

\newcommand{\recipeBarUseFoodDefaults}{%
    \gdef\recipeBarMode{food}%
    \setlength{\spiritSegmentHeight}{\dimexpr\paperheight/3\relax}%
}

\newcommand{\recipeBarInitializeFromDocumentClass}{%
    \ifx\recipeCardCategory\recipeCardCategoryFood
        \recipeBarUseFoodDefaults
    \else
        \recipeBarUseCocktailDefaults
    \fi
}

\newcommand{\recipeDrawEdgeBarAt}[1]{%
    \draw[draw=black!25,line width=0.2pt] (#1,0) rectangle ++(\spiritStripWidth,-\paperheight);
    \ifx\recipeBarMode\recipeCardCategoryFood
        \foreach \i in {1,2}{
            \draw[draw=black!25,line width=0.2pt] (#1,-\i*\spiritSegmentHeight) -- ++(\spiritStripWidth,0);
        }
        \ifnum\recipeTypeSegmentIndex=0 \fill[recipeTypeBakery] (#1,0) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeTypeSegmentIndex=1 \fill[recipeTypePrimi] (#1,-\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeTypeSegmentIndex=2 \fill[recipeTypeSecondi] (#1,-2\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
    \else
        \foreach \i in {1,2,3,4}{
            \draw[draw=black!25,line width=0.2pt] (#1,-\i*\spiritSegmentHeight) -- ++(\spiritStripWidth,0);
        }
        \ifnum\recipeSpiritSegmentIndex=0 \fill[spiritGin] (#1,0) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeSpiritSegmentIndex=1 \fill[spiritWhiskey] (#1,-\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeSpiritSegmentIndex=2 \fill[spiritRum] (#1,-2\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeSpiritSegmentIndex=3 \fill[spiritVodka] (#1,-3\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
        \ifnum\recipeSpiritSegmentIndex=4 \fill[spiritTequila] (#1,-4\spiritSegmentHeight) rectangle ++(\spiritStripWidth,-\spiritSegmentHeight);\fi
    \fi
}

\newcommand{\drawFrontEdgeBar}{%
    \AddToShipoutPictureFG*{%
        \AtPageUpperLeft{%
            \begin{tikzpicture}[overlay]
                \pgfmathsetlengthmacro{\spiritX}{\paperwidth-\spiritStripInset-\spiritStripWidth}
                \recipeDrawEdgeBarAt{\spiritX}
            \end{tikzpicture}%
        }%
    }%
}

\newcommand{\setBaseSpirit}[1]{%
    \recipeBarUseCocktailDefaults
    \gdef\recipeSpiritArg{#1}%
    \gdef\recipeSpiritSegmentIndex{0}%
    \gdef\recipeSpiritGin{Gin}%
    \gdef\recipeSpiritGinLower{gin}%
    \gdef\recipeSpiritWhiskey{Whiskey}%
    \gdef\recipeSpiritWhiskeyLower{whiskey}%
    \gdef\recipeSpiritRum{Rum}%
    \gdef\recipeSpiritRumLower{rum}%
    \gdef\recipeSpiritVodka{Vodka}%
    \gdef\recipeSpiritVodkaLower{vodka}%
    \gdef\recipeSpiritTequila{Tequila}%
    \gdef\recipeSpiritTequilaLower{tequila}%
    \ifx\recipeSpiritArg\recipeSpiritGinLower
        \gdef\recipeSpiritSegmentIndex{0}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritWhiskey
        \gdef\recipeSpiritSegmentIndex{1}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritWhiskeyLower
        \gdef\recipeSpiritSegmentIndex{1}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritRum
        \gdef\recipeSpiritSegmentIndex{2}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritRumLower
        \gdef\recipeSpiritSegmentIndex{2}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritVodka
        \gdef\recipeSpiritSegmentIndex{3}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritVodkaLower
        \gdef\recipeSpiritSegmentIndex{3}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritTequila
        \gdef\recipeSpiritSegmentIndex{4}%
    \fi
    \ifx\recipeSpiritArg\recipeSpiritTequilaLower
        \gdef\recipeSpiritSegmentIndex{4}%
    \fi
    \drawFrontEdgeBar
}

\newcommand{\setRecipeType}[1]{%
    \recipeBarUseFoodDefaults
    \gdef\recipeTypeArg{#1}%
    \gdef\recipeTypeSegmentIndex{0}%
    \gdef\recipeTypePrimi{Primi}%
    \gdef\recipeTypePrimiLower{primi}%
    \gdef\recipeTypeSecondi{Secondi}%
    \gdef\recipeTypeSecondiLower{secondi}%
    \ifx\recipeTypeArg\recipeTypePrimi
        \gdef\recipeTypeSegmentIndex{1}%
    \fi
    \ifx\recipeTypeArg\recipeTypePrimiLower
        \gdef\recipeTypeSegmentIndex{1}%
    \fi
    \ifx\recipeTypeArg\recipeTypeSecondi
        \gdef\recipeTypeSegmentIndex{2}%
    \fi
    \ifx\recipeTypeArg\recipeTypeSecondiLower
        \gdef\recipeTypeSegmentIndex{2}%
    \fi
    \drawFrontEdgeBar
}

% Mirror the edge marker onto the left side of the back page.
\newcommand{\drawBackMirrorRecipeBar}{
    \AddToShipoutPictureFG*{%
        \AtPageUpperLeft{%
            \begin{tikzpicture}[overlay]
                \pgfmathsetlengthmacro{\spiritXL}{\spiritStripInset}
                \recipeDrawEdgeBarAt{\spiritXL}
            \end{tikzpicture}%
        }%
    }%
}
\newcommand{\drawBackMirrorSpiritBar}{\drawBackMirrorRecipeBar}
\AtBeginDocument{\recipeBarInitializeFromDocumentClass}

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
\newcommand{\recipeTitle}[1]{{\color[HTML]{A51C30} \Huge \sketchfont #1}}
\newcommand{\recipeTitleDivider}{\par\vspace{1pt}}

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

% Cocktail Metadata (named arguments):
%   \cocktailMeta{base=Gin,glass=Rocks,method=Built,ice=Large Cube,strength=High,garnish=Orange Peel}
% Backward-compatible positional helper:
%   \cocktailMetaPositional{Rocks}{Built}{Large Cube}{High}{Orange Peel}
\ExplSyntaxOn
\tl_new:N \l_cocktail_meta_base_tl
\tl_new:N \l_cocktail_meta_glass_tl
\tl_new:N \l_cocktail_meta_method_tl
\tl_new:N \l_cocktail_meta_ice_tl
\tl_new:N \l_cocktail_meta_strength_tl
\tl_new:N \l_cocktail_meta_garnish_tl

\keys_define:nn { cocktail/meta }
{
    base     .tl_set:N = \l_cocktail_meta_base_tl,
    glass    .tl_set:N = \l_cocktail_meta_glass_tl,
    method   .tl_set:N = \l_cocktail_meta_method_tl,
    ice      .tl_set:N = \l_cocktail_meta_ice_tl,
    strength .tl_set:N = \l_cocktail_meta_strength_tl,
    garnish  .tl_set:N = \l_cocktail_meta_garnish_tl
}

\cs_new_protected:Npn \cocktail_meta_render:
{
    \small
    \cocktailGlassWithLabel{\tl_use:N \l_cocktail_meta_glass_tl}
    \quad
    \cocktailMethodWithLabel{\tl_use:N \l_cocktail_meta_method_tl}
    \quad
    \tl_use:N \l_cocktail_meta_ice_tl
    \quad
    \tl_use:N \l_cocktail_meta_strength_tl
    \quad
    \tl_use:N \l_cocktail_meta_garnish_tl
    \par
}

\NewDocumentCommand{\cocktailMeta}{m}
{
    \tl_clear:N \l_cocktail_meta_base_tl
    \tl_clear:N \l_cocktail_meta_glass_tl
    \tl_clear:N \l_cocktail_meta_method_tl
    \tl_clear:N \l_cocktail_meta_ice_tl
    \tl_clear:N \l_cocktail_meta_strength_tl
    \tl_clear:N \l_cocktail_meta_garnish_tl
    \keys_set:nn { cocktail/meta } { #1 }
    \tl_if_blank:VTF \l_cocktail_meta_base_tl
        { }
        { \exp_args:NV \setBaseSpirit \l_cocktail_meta_base_tl }
    \cocktail_meta_render:
}

\NewDocumentCommand{\cocktailMetaPositional}{m m m m m}
{
    \cocktailMeta
    {
        glass={#1},
        method={#2},
        ice={#3},
        strength={#4},
        garnish={#5}
    }
}
\ExplSyntaxOff

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
    \let\group\recipeIngredientGroup
}{
    \end{itemize}
    \end{minipage}\hfill
}
% Ingredient line is split into quantity and description so formatting can evolve later.
\newcommand{\ingredient}[2]{\item #1\hspace{0.5em}#2}
\newlength{\recipeIngredientGroupOffset}
\newcommand{\recipeIngredientGroup}[1]{%
    \settowidth{\recipeIngredientGroupOffset}{\labelitemi}%
    \item[]\vspace{2pt}%
    \hspace*{-\labelsep}\hspace*{-\recipeIngredientGroupOffset}%
    \textbf{\color{recipeRed}\footnotesize #1}%
    \vspace{-1pt}%
}

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
