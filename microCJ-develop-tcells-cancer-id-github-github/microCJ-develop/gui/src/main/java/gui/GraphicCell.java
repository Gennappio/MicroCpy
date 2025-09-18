package gui;

import core.Cell;
import geom.Point;
import graph.Edge;
import graph.Node;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;
import javafx.scene.shape.Polygon;
import javafx.scene.shape.Rectangle;
import javafx.scene.shape.Shape;
import javafx.scene.text.Text;
import org.jgrapht.alg.drawing.FRLayoutAlgorithm2D;
import org.jgrapht.alg.drawing.model.Point2D;
import graphfx.ActionOnClick;
import graphfx.GraphDisplay;

import java.util.Arrays;
import java.util.Objects;

abstract class GraphicCell {
	private static final double IDEAL_GRAPH_SIZE = 600;
	private static final Color darkOff = Color.web("EE8DA5");
	private static final Color off = Color.web("FADBE3");
	private static final Color darkOn = Color.web("8DEED6");
	private static final Color on = Color.web("D5F9F0");
	private static final double[] triangleCoordinates = {-1., -Math.sqrt(3) / 2, 0., Math.sqrt(3) / 2, 1., -Math.sqrt(3) / 2};
	private double graphSize;
	private final Cell cell;
	private final Palette palette;
	private final double radius;
	private GraphDisplay<Node, Edge> graphDisplay;
	private Point location;

	GraphicCell(Cell cell, Palette palette, double radius) {
		this.cell = cell;
		this.palette = palette;
		this.radius = radius;
		createNode(radius);
		moveTo(cellLocationToGraphicLocation(cell.getLocation()));
	}

	abstract void createNode(double radius);

	abstract javafx.scene.Node getNode();

	abstract void moveTo(Point target);

	void setLocation(Point location) {
		this.location = location;
	}

	GraphDisplay<Node, Edge> renderGraphDisplay(double scale) {
		if (graphDisplay == null) {
			graphSize = IDEAL_GRAPH_SIZE * scale;
			graphDisplay = (new GraphDisplay<>(getCell().getNetwork().getGraph()))
					.size(graphSize)
					.algorithm(new FRLayoutAlgorithm2D<>(1000, 0.8))
					.vertices(node -> {
						Shape vertex = switch(node.getNodeType()){
							case INPUT -> new Polygon(multiplyArray(triangleCoordinates, graphSize /50));
							case GENE -> new Circle(graphSize / 50);
							case FATE -> new Rectangle(-graphSize /50, -graphSize /50, graphSize / 25, graphSize / 25);
						};
						vertex.setFill(node.isActive() ? on : off);
						vertex.setStroke(node.isActive() ? darkOn : darkOff);
						vertex.setStrokeWidth(graphSize /150);
						return vertex;
					})
					.labels(point2D -> new Point2D(point2D.getX() + (7 * scale), point2D.getY() + (7 * scale)),
							node -> new Text(node.getTag()))
					.edges(true, (edge, path) -> {
						path.setFill(edge.isPositive() ? darkOn : darkOff);
						path.setStrokeWidth(1.5*scale);
						path.getStrokeDashArray().addAll(20., 10.);
						return path;
					})
					.withVertexUpdater((node, shape) -> {
						shape.setFill(node.isActive() ? on : off);
						shape.setStroke(node.isActive() ? darkOn : darkOff);
					})
					.withActionOnClick(ActionOnClick.HIGHLIGHT_ALL_CONNECTED_VERTICES);
			graphDisplay.render();
			return graphDisplay;
		}
		else throw new IllegalStateException("GraphDisplay has already been rendered. To change the scale, call getGraphDisplay().rescale(double scale)");
	}

	Cell getCell() {
		return cell;
	}

	private static double[] multiplyArray(double[] array, double d){
		return Arrays.stream(array).map(a -> a * d).toArray();
	}

	GraphDisplay<Node, Edge> getGraphDisplay() {
		return Objects.requireNonNull(graphDisplay, "GraphDisplay hasn't been rendered yet");
	}

	GraphDisplay<Node, Edge> getGraphDisplayAfterRendering(double scale){
		if(graphDisplay == null) graphDisplay = renderGraphDisplay(scale);
		return graphDisplay;
	}

	void rescaleGraph(double scale){
		double rescaleFactor = IDEAL_GRAPH_SIZE * scale / 2;
		graphDisplay.rescale(rescaleFactor,
				shape -> {
					shape.setScaleX(scale);
					shape.setScaleY(scale);
				});
	}

	boolean updateLocation(){
		boolean updated = ! location.equals(cellLocationToGraphicLocation(cell.getLocation()));
		if(updated) moveTo(cellLocationToGraphicLocation(cell.getLocation()));
		return updated;
	}

	abstract void setNecrotic();

	abstract Point cellLocationToGraphicLocation(Point cellLocation);

	Palette getPalette() {
		return palette;
	}

	double getRadius() {
		return radius;
	}
}
