package gui;

import graph.Subpopulation;
import javafx.scene.paint.Color;
import javafx.scene.paint.Material;
import javafx.scene.paint.PhongMaterial;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class Palette {
	private static final Color[] DEFAULT_PALETTE = {Color.AQUA, Color.CORAL, Color.DARKSEAGREEN, Color.DARKORANGE, Color.BLUE, Color.GREEN, Color.YELLOW, Color.YELLOWGREEN, Color.PURPLE, Color.BROWN, Color.ORANGE, Color.ORCHID}; //todo improve
	private static final Color DEFAULT_NECROSIS_COLOR = Color.DARKRED;
	private static final Color DEFAULT_NO_GROUP_COLOR = Color.DARKGREY;
	private Color necrosisColor = DEFAULT_NECROSIS_COLOR;
	private Color noGroupColor = DEFAULT_NO_GROUP_COLOR;
	private Color xColor = Color.DARKRED;
	private Color yColor = Color.DARKGREEN;
	private Color zColor = Color.DARKBLUE;
	private Map<Subpopulation, Color> colorPalette = new HashMap<>();
	private static Color EGFRp53mPTENm = Color.web("1AC58A");
	private static Color EGFRpp53m =	Color.web("A3A500");
	private static Color EGFRp = Color.web("F87E75");
	private static Color p53m = Color.web("23BAF7");
	private static Color wt = Color.web("E76BF3");
	private static Map<String, Color> defaultPops = Map.of(
			"EGFR+p53-PTEN-", EGFRp53mPTENm,
			"EGFR+p53-", EGFRpp53m,
			"EGFR+", EGFRp,
			"p53-", p53m,
			"WT", wt);
	private Palette(){}

	public static Palette from(List<Subpopulation> subpopulations){
		Palette palette = new Palette();
		for (int i = 0; i < subpopulations.size(); i++) {
			Subpopulation subpop = subpopulations.get(i);
			Color color;
			if(defaultPops.containsKey(subpop.getName())){
				color = defaultPops.get(subpop.getName());
			} else {
				color = i < DEFAULT_PALETTE.length ? DEFAULT_PALETTE[i] : getRandomColor();
			}

			palette.colorPalette.put(subpop, color);
		}
		return palette;
	}

	public Color getColorFor(Subpopulation group){
		return group != null ? colorPalette.get(group) : getNoGroupColor();
	}

	public Material getMaterialFor(Subpopulation group) {
		return getMaterialWith(getColorFor(group));
	}

	/**
	 * Returns the color with index i from the active palette
	 * @param i the index of the color in the active palette
	 * @return a color from the active palette
	 */
	public Color getColor(int i){
		return DEFAULT_PALETTE[i];
	}

	public Color getNecrosisColor() {
		return necrosisColor;
	}

	public Color getNoGroupColor() {
		return noGroupColor;
	}

	public Material getNecrosisMaterial() {
		return getMaterialWith(necrosisColor);
	}

	public Material getNoGroupMaterial() {
		return getMaterialWith(noGroupColor);
	}

	public Color getXColor() {
		return xColor;
	}

	public Color getYColor() {
		return yColor;
	}

	public Color getZColor() {
		return zColor;
	}

	public Material getXMaterial() {
		return getMaterialWith(xColor);
	}

	public Material getYMaterial() {
		return getMaterialWith(yColor);
	}

	public Material getZMaterial() {
		return getMaterialWith(zColor);
	}

	private static Color getRandomColor(){
		var r = ThreadLocalRandom.current();
		return Color.color(r.nextDouble(), r.nextDouble(), r.nextDouble());
	}

	private static PhongMaterial getMaterialWith(Color color) {
		PhongMaterial phongMaterial = new PhongMaterial();
		phongMaterial.setDiffuseColor(color);
		phongMaterial.setSpecularColor(color.brighter());
		return phongMaterial;
	}

}
