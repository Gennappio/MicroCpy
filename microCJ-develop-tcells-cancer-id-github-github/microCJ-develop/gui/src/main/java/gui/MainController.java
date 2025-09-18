/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package gui;

import core.Cell;
import core.SettingsProvider;
import core.World;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.beans.property.DoubleProperty;
import javafx.beans.property.SimpleDoubleProperty;
import javafx.embed.swing.SwingFXUtils;
import javafx.fxml.FXML;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Group;
import javafx.scene.Scene;
import javafx.scene.SubScene;
import javafx.scene.chart.CategoryAxis;
import javafx.scene.chart.LineChart;
import javafx.scene.chart.NumberAxis;
import javafx.scene.chart.XYChart;
import javafx.scene.control.*;
import javafx.scene.image.Image;
import javafx.scene.image.WritableImage;
import javafx.scene.input.MouseEvent;
import javafx.scene.input.ScrollEvent;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;
import javafx.scene.text.Font;
import javafx.scene.text.Text;
import javafx.stage.Popup;
import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.tree.ImmutableNode;
import update.Updatable;
import update.Update;
import update.UpdateFlag;

import javax.imageio.ImageIO;
import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

import static core.SettingsProvider.SETTINGS_PROVIDER;

public abstract class MainController {
	@FXML
	private Slider slZoom;
	@FXML
	private MenuBar mbMain;
	@FXML
	private Button bPause;
	@FXML
	private Label lTime;
	@FXML
	private BorderPane bpMain;
	@FXML
	private BorderPane bpRight;
	@FXML
	private BorderPane bpCenter;
	@FXML
	private Label totalCount;
	@FXML
	private Label totalcancerCount;
	@FXML
	private Label totalcd4Count;
	@FXML
	private Label mutCounts;
	@FXML
	private Button bClose;
	private final DoubleProperty scale = new SimpleDoubleProperty(1);
	private StackPane graphPane;
	private final Group nodes = new Group();
	static final double CELL_RADIUS = 10;
	private static final double IDEAL_WIDTH = 1920;
	private static final double IDEAL_CELL_SCENE_WIDTH = 800;
	private static final double IDEAL_GENES_SCENE_WIDTH = 800;
	private final List<GraphicCell> graphicCells = new ArrayList<>();
	private final List<Image> snaps = new ArrayList<>();
	@FXML
	private Label lInfo;
	private final Popup settingsPopup = new Popup();
	private GraphicCell selectedCell;
	@FXML
	private Button bSettings;
	private Scene mainScene;
	private boolean paused = true;
	private SubScene cellsScene;
	private SubScene genesScene;
	@FXML
	private Menu mPlotting;
	private final World world = new World();
	private Palette palette;
	private final Map<String, XYChart.Series<String, Number>> prolifData = new HashMap<>();
	private LineChart<String, Number> prolifChart;
	private int snapshots;

	@FXML //Called when loading the FXML file
	public void initialize() {
		setup(); //creates tumor

		//prepare graph pane
		graphPane = new StackPane();
		graphPane.setStyle("-fx-background-color: white;");
		graphPane.setPadding(new Insets(20 * scale.get()));

		//layout
		genesScene = new SubScene(graphPane, 100, 100);
		cellsScene = createCellsSubScene();

		bpRight.setCenter(genesScene);
		BorderPane.setAlignment(genesScene, Pos.CENTER);

		bpCenter.setCenter(cellsScene);
		BorderPane.setAlignment(cellsScene, Pos.CENTER);
		handleMouse(cellsScene);

		//general info
		StringJoiner sj = new StringJoiner(System.lineSeparator());
		int max = 7;
		for (Map.Entry<String, Integer> entry : world.getTumor().getSubpopulationCounts().entrySet()) {
			if(max == 0){
				sj.add("...");
				break;
			}
			sj.add(entry.getKey() + ": " + entry.getValue());
			max--;
		}

		mutCounts.setText(sj.toString());
		totalCount.setText("Total count: " + world.getTumor().getTotalCount());
		mutCounts.setFont(new Font(20));
		totalCount.setFont(new Font(20));
		mutCounts.setTextOverrun(OverrunStyle.WORD_ELLIPSIS);

		//cell info
		lInfo.setTextOverrun(OverrunStyle.WORD_ELLIPSIS);
		lInfo.setWrapText(true);

		//Button actions
		bClose.setCancelButton(true); //makes it responsive to ESC
		bClose.setOnAction(event -> {
			selectedCell = null;
			lInfo.setText("");
			graphPane.getChildren().clear();
		});

		bPause.setOnAction(event -> {
			paused = !paused;
			if (paused) pause();
			else unpause();
		});

		slZoom.valueProperty().addListener((observable, oldValue, newValue) ->
				handleZoomSlider(oldValue.doubleValue(), newValue.doubleValue()));

		buildPlottingMenu();
	}

	protected abstract void handleZoomSlider(double oldValue, double newValue);

	private void buildPlottingMenu() {
		CheckMenuItem prolifPlot = new CheckMenuItem("Proliferation plot");
		prolifPlot.setOnAction(event -> showProliferationPlot());
		mPlotting.getItems().add(prolifPlot);
	}

	protected abstract SubScene createCellsSubScene();

	private void unpause() {
		world.start();
		bPause.setText("Pause");
	}

	private void pause() {
		world.pause();
		bPause.setText("Start");
	}

	protected void setup() {
		boolean isThis2D = this instanceof MainController2D;
		world.setup(false, isThis2D); //false - no multiple worlds running
		palette = Palette.from(world.getTumor().getMutationGroups());
		generateWorld();
		mutCounts.setText(world.getTumor().getSubpopulationCounts().toString());
		totalCount.setText("Total Count: " + world.getTumor().getTotalCount());
		snapshots = world.getSnapshots();

		//initialize chart data
		XYChart.Series<String, Number> totalSeries = new XYChart.Series<>();
		totalSeries.setName("Total Count");
		prolifData.put("Total Count", totalSeries);
		for (String mutation : world.getTumor().getSubpopulationNames()) {
			XYChart.Series<String, Number> series = new XYChart.Series<>();
			series.setName(mutation);
			prolifData.put(mutation, series);
		}
	}

	/**
	 * Deletes all cells and create the tumor again with the new settings
	 */
	private void reset() {
		nodes.getChildren().removeAll(graphicCells.stream().map(GraphicCell::getNode).collect(Collectors.toList())); //remove all cell nodes
		graphicCells.clear();
		lTime.setText("");
		lInfo.setText("");
		slZoom.setValue(50);
		graphPane.getChildren().clear();
		world.reset();
		setup(); //setup again with the new settings
	}

	void setScene(Scene scene) { //called by Main after loading the fxml and setting the controller
		mainScene = scene;
		buildSettingsPopup();
		bSettings.setOnAction(event -> settingsPopup.show(scene.getWindow()));
		//resize components relative to scene width
		resize(scene.getWidth());
		mainScene.widthProperty().addListener((observable, oldValue, newValue) -> resize(newValue.doubleValue()));
		handleKeyboard(scene);
	}

	protected void resize(double width) { //todo rework using bindings to scale, or simply to width, which is already a property
		cellsScene.setWidth(width * (IDEAL_CELL_SCENE_WIDTH / IDEAL_WIDTH));
		cellsScene.setHeight(cellsScene.getWidth());
		genesScene.setWidth(width * (IDEAL_GENES_SCENE_WIDTH / IDEAL_WIDTH));
		genesScene.setHeight(genesScene.getWidth() - 50); //leave space for labels
		scale.set(width /IDEAL_WIDTH);
		Font newSize = new Font(20 * scale.get());
		mutCounts.setFont(newSize);
		totalCount.setFont(newSize);
		lInfo.setFont(newSize);
		if(selectedCell!= null) selectedCell.rescaleGraph(scale.get());
	}

	private void buildSettingsPopup() {
		//create one input box for every setting available
		VBox vbSettings = new VBox(10);
		vbSettings.setPadding(new Insets(10));
		Map<String, TextField> inputs = new HashMap<>();

		HierarchicalConfiguration<ImmutableNode> generalSettings = SETTINGS_PROVIDER.getSettings().configurationAt("general");
		for (Iterator<String> it = generalSettings.getKeys(); it.hasNext(); ) {
			String key = it.next();
			HBox inputRow = new HBox(10);
			Label title = new Label(key);
			String cuValue = generalSettings.getString(key);
			TextField textField = new TextField(cuValue);
			inputs.put(key, textField);
			inputRow.getChildren().addAll(title, textField);
			vbSettings.getChildren().add(inputRow);
		}

		//create Accept button
		Button bAccept = new Button("Accept and restart");
		bAccept.setOnAction(event -> {
			//reads every field and set it in Settings
			for (String key : inputs.keySet()) {
				String input = inputs.get(key).getText();
				SETTINGS_PROVIDER.getSettings().setProperty("general." + key, input);
			}
			SETTINGS_PROVIDER.writeUserSettingsToFile();
			settingsPopup.hide();
			reset();
		});

		//create Cancel button
		Button bCancel = new Button("Cancel");
		bCancel.setOnAction(event -> settingsPopup.hide());

		//create Reset to default button
		Button bDefault = new Button("Reset to default");
		bDefault.setOnAction(event -> {
			SETTINGS_PROVIDER.loadDefaultSettings();
			settingsPopup.hide();
			buildSettingsPopup();
			reset();
		});

		//create Exit button
		Button bExit = new Button("Exit");
		bExit.setOnAction(event -> {
			saveImages();
			world.finish();
			Platform.exit();
		});

		//create About popup and button
		final Popup aboutPopup = new Popup();
		Text tAbout = new Text("""
				MicroCJ created by Pedro Victori (Buffa lab)\s
				Released under the Apache License 2.0.\s
				https://github.com/CBigOxf/microCJ\s
				https://www.oncology.ox.ac.uk/team/francesca-buffa""");
		tAbout.setFont(new Font(20));
		Button bCloseAbout = new Button("Close");
		bCloseAbout.setOnAction(event -> aboutPopup.hide());
		VBox aboutVBox = new VBox(10, tAbout, bCloseAbout);
		aboutPopup.getScene().setFill(Color.DARKGREY);
		aboutPopup.getContent().add(aboutVBox);
		aboutPopup.setAutoHide(true);
		Button bAbout = new Button("About");
		bAbout.setOnAction(event -> aboutPopup.show(mainScene.getWindow()));

		//add all buttons to boxes
		HBox buttons1 = new HBox(10, bAccept, bCancel); //add buttons to hbox1
		HBox buttons2 = new HBox(10, bDefault, bAbout, bExit); //add buttons to hbox2
		VBox allButtons = new VBox(10, buttons1, buttons2); //add buttons to vbox

		vbSettings.getChildren().add(allButtons);

		settingsPopup.getContent().add(vbSettings);
		settingsPopup.getScene().setFill(Color.web("#708090", 0.7));

		//makes settings autohide when focus lost
		settingsPopup.setAutoHide(true);
	}

	protected static final double CONTROL_MULTIPLIER = 0.1;
	protected static final double SHIFT_MULTIPLIER = 10.0;
	private double mousePosX;
	private double mousePosY;
	private double mouseOldX;
	private double mouseOldY;
	private double mouseDeltaX;
	private double mouseDeltaY;

	private void handleMouse(SubScene scene) {
		scene.setOnMousePressed(me -> {
			mousePosX = me.getSceneX();
			mousePosY = me.getSceneY();
			mouseOldX = me.getSceneX();
			mouseOldY = me.getSceneY();
		});
		scene.setOnMouseDragged(me -> {
			mouseOldX = mousePosX;
			mouseOldY = mousePosY;
			mousePosX = me.getSceneX();
			mousePosY = me.getSceneY();
			mouseDeltaX = (mousePosX - mouseOldX);
			mouseDeltaY = (mousePosY - mouseOldY);

			handleMouseEvent(me, mouseDeltaX, mouseDeltaY);
		});

		scene.setOnScroll(this::handleScrollEvent);

		slZoom.setOnScroll(event -> slZoom.adjustValue(slZoom.getValue() + event.getDeltaY() / 10));
	}

	protected abstract void handleScrollEvent(ScrollEvent event);

	protected abstract void handleMouseEvent(MouseEvent me, double mouseDeltaX, double mouseDeltaY);

	protected abstract void handleKeyboard(Scene scene);

	private void generateWorld() { //called by setup() after resetting the World
		for (Cell cell : world.getTumor().getCellList()) addNewCell(cell);

		world.getPaceMaker().atEveryStep(() -> Platform.runLater(() -> {
			runRecurrentGuiUpdates();
			executeCellUpdates();

			//take snapshot
			int step = world.getPaceMaker().getStep();
			if(snapshots > 0 && (step % snapshots == 0)){ //if snapshots are on and this step is a multiple of the frequency
				snaps.add(mainScene.snapshot(null));
				if(step % 500 == 0){
					saveImages();
				}
			}
		}));
	}

	protected void runRecurrentGuiUpdates() {
		Map<String, Integer> mutationGroupsCounts = world.getTumor().getSubpopulationAliveCounts();
		int step = world.getPaceMaker().getStep();
		lTime.setText("Time Point: " + step);
		totalCount.setText("Total Count: " + world.getTumor().getTotalAliveCount());
		mutCounts.setText(mutationGroupsCounts.entrySet().stream()
				.map(entry -> entry.getKey() + ": " + entry.getValue())
				.collect(Collectors.joining(System.lineSeparator())));

		//update gene graph and cell info
		if (selectedCell != null) {
			selectedCell.getGraphDisplay().update(); //update currently shown gene graph
			lInfo.setText(truncateCellInfo(selectedCell.getCell())); //update currently shown cell info
		}

		//Proliferation data for charts
		prolifData.get("Total Count").getData().add(new XYChart.Data<>(Integer.toString(step), world.getTumor().getTotalAliveCount()));
		for (String mut : mutationGroupsCounts.keySet()) {
			prolifData.get(mut).getData().add(new XYChart.Data<>(
					Integer.toString(step),
					mutationGroupsCounts.get(mut)
			));
		}
	}

	private void executeCellUpdates() {
		boolean shovingPending = false;
		while (world.getRemainingGuiUpdates() > 0) {
			Update<UpdateFlag, Updatable> update = world.popUpdateFromGuiQueue(); //retrieve an update from the queue, in priority order
			Cell cell = (Cell) update.getUpdatable(); //right now  all updatable are Cells

			if (update.getFlag() == UpdateFlag.NEW_CELL) {
				shovingPending = world.isShovingActive();
				addNewCell(cell);
			} else {
				//find the graphic cell that is being updated, if it wasn't updated already (throttling)
				var graphicCellOptional = graphicCells.stream()
						.filter(thisGraphicCell -> thisGraphicCell.getCell().equals(cell)).findAny();
				if(graphicCellOptional.isPresent()) {
					var graphicCell = graphicCellOptional.get();
					if (update.getFlag() == UpdateFlag.DEAD_CELL) {
						nodes.getChildren().remove(graphicCell.getNode());
						graphicCells.remove(graphicCell);
					} else if (update.getFlag() == UpdateFlag.NECROTIC_CELL) {
						graphicCell.setNecrotic(); //changes appearance
					}
				}
			}
			if (shovingPending) {
				for (GraphicCell graphicCell : graphicCells) {
					graphicCell.updateLocation();
				}
			}
		}
	}

	private void addNewCell(Cell cell){
		GraphicCell graphicCell = createGraphicCell(cell);
		nodes.getChildren().add(graphicCell.getNode());
		addEventToCell(graphicCell);
		graphicCells.add(graphicCell);
	}

	abstract GraphicCell createGraphicCell(Cell cell);

	private void addEventToCell(GraphicCell cell) {
		cell.getNode().setOnMouseClicked(event -> {
			selectedCell = cell;
			graphPane.getChildren().clear();
			graphPane.getChildren().add(cell.getGraphDisplayAfterRendering(scale.get()));
			lInfo.setText(truncateCellInfo(cell.getCell()));
		});
	}

	void saveImages() {
		if(snapshots > 0) {
			for (int i = 0; i < snaps.size(); i++) {
				saveImage(snaps.get(i), "snap" + i);
			}
		}
	}

	private void saveImage(Image image, String name) {
		File file = new File("snaps/" + name + ".png");
		try {
			ImageIO.write(SwingFXUtils.fromFXImage(image, null), "png", file);
		} catch (IOException ioe) {
			ioe.printStackTrace();
		}
	}

	private void buildChart() {
		final CategoryAxis xTime = new CategoryAxis();
		final NumberAxis ynCells = new NumberAxis();
		xTime.setLabel("Time Point");
		xTime.setAnimated(false);
		ynCells.setLabel("Number of Cells");
		ynCells.setAnimated(false);

		prolifChart = new LineChart<>(xTime, ynCells);
		prolifChart.setTitle("Proliferation");
		prolifChart.setAnimated(false);

		for (String series : prolifData.keySet()) {
			prolifChart.getData().add(prolifData.get(series));
		}
	}

	private void showProliferationPlot() {
		if (prolifChart == null) {
			buildChart();
		}
		selectedCell = null;
		graphPane.getChildren().clear();
		graphPane.getChildren().add(prolifChart);
	}

	private String truncateCellInfo(Cell cell) {
		String info = cell.getInfo();
		StringJoiner joiner = new StringJoiner(System.lineSeparator());
		for (String line : info.split(System.lineSeparator())) {
			if(line.length() > 50){
				line = line.substring(0, 50);
				if(line.charAt(49) == ',') line = line.substring(0, 48);
				line = line + "...";
			}
			joiner.add(line);
		}
		return joiner.toString();
	}

	protected Palette getPalette() {
		return palette;
	}

	protected Group getNodes() {
		return nodes;
	}

	protected World getWorld() {
		return world;
	}

	protected double getScale() { //todo check usages and replace them with bindings if possible
		return scale.get();
	}

	protected DoubleProperty scaleProperty() {
		return scale;
	}

	protected StackPane getGraphPane() {
		return graphPane;
	}

	protected List<GraphicCell> getGraphicCells() {
		return graphicCells;
	}

	public Scene getMainScene() {
		return mainScene;
	}

	public Slider getSlZoom() {
		return slZoom;
	}
}
