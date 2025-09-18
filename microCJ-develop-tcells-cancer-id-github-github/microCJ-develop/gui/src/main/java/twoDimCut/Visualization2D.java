package twoDimCut;

import core.Cell3D;
import gui.Palette;
import javafx.scene.Node;
import javafx.scene.Parent;

import java.util.List;
import java.util.stream.Collectors;

public class Visualization2D extends Parent{
	private List<Cell3D> allCells;
	private Palette palette;
	private Panel2D panel;
	private double scale;
	private boolean active = false;

	public Visualization2D(List<Cell3D> allCells, Palette palette, Panel2D panel, double scale) { //todo rewrite class
		this.allCells = allCells;
		this.palette = palette;
		this.panel = panel;
		this.scale = scale;
		renderVisualization();
		panel.setOnMove(event -> renderVisualization());
	}

	private void renderVisualization(){
		getChildren().clear();
		var cutCells =  allCells.stream()
				.filter(cell -> {
					double cellY = cell.getPoint3D().getY();
					double cellR = cell.getRadius();
					return Math.abs(panel.getPos() - cellY) < cellR; }) //if cells are at [cell radius] distance or less from the panel in the Y axis ("height")
				.map(cell -> {
					if(cell.isNecrotic()) return new CutCell2D(cell, palette.getNecrosisColor(), scale);
					else return new CutCell2D(cell, palette.getColorFor(cell.getSubpopulation().orElse(null)), scale);})
				.collect(Collectors.toList());

		getChildren().addAll(cutCells);
	}




	/**
	 * Updates the cell list used to draw the 2D visualization
	 * @param allCells a list of all the cells in the tumor
	 */
	public void setCellList(List<Cell3D> allCells) {
		this.allCells = allCells;
		renderVisualization();
	}

	/**
	 * Resizes all components of the 2D visualization using the provided factor
	 * @param scale the factor by which the size of all components will be multiplied.
	 */
	public void setScale(double scale) {
		this.scale = scale;
		for (Node node : getChildren()) {
			if(node instanceof CutCell2D) {
				CutCell2D cutCell2D = (CutCell2D) node;
				cutCell2D.setScale(scale);
			} else throw new IllegalStateException("Visualization 2D has nodes that are not of class CutCell2D");
		}
	}

	public void switchActive() {
		active = ! active;
	}

	public boolean isActive() {
		return active;
	}
}
