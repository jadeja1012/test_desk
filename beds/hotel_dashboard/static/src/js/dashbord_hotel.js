/** @odoo-module **/
import { registry } from "@web/core/registry";
// import { KpiCard } from "./kpi_card";
// import { ChartRender } from "./chart_render";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { getColor } from "@web/core/colors/colors";
import { _t } from "@web/core/l10n/translation";

const { Component,onWillStart,useRef,onMounted,useState } = owl
var selected_days = new Array();
var mousedown
var selection =  new Array();
var hotelname
var froomname
var croomname
var mroomname
let intervalId = null;

export class CalenderDashboard extends Component{
    setup(){
		super.setup();
		this.orm = useService("orm");
		this.actionService = useService("action");
		this.shop_id = "";
		onMounted(() => {
			this.month_function();
		});
		this.start();
	
		this.from_date = ''; // Use `this` for component properties
		this.to_date = '';
		this.view_type = 'month';
		this.date_detail = '';
	
		
		
    }
	

	async start() {
        try {
           
            var shop = await this.orm.call('hotel.room_type', 'list_shop', [0], {});
            console.log("Shop data fetched successfully:", shop);
    
            
            var shopsSelect = document.getElementById("shops");
    
            if (!shopsSelect) {
                throw new Error("Element with ID 'shops' not found in the DOM.");
            }
    
           
            var optionToRemove = shopsSelect.querySelector('option[value="1"]');
    
            if (optionToRemove) {
                shopsSelect.removeChild(optionToRemove);
            } else {
                console.log("Option with value '1' not found, skipping removal.");
            }
    
    
            
            for (var i = 0; i < shop.length; i++) {
                var newOption = document.createElement("option");
                newOption.textContent = shop[i].name;
                newOption.value = shop[i].id;
                shopsSelect.appendChild(newOption);
            }
        
           
            // this.reload();
            this.scheduleDataReload();
    
        } catch (error) {
            
            console.error("Error in start():", error.message);
        }
    }
	async total_detail() {
        try {
            
            var shopsSelect = document.getElementById('shops');
            if (!shopsSelect) throw new Error("Element with ID 'shops' not found.");
    
            var shop_id = shopsSelect.value;
    
            if (!shop_id) throw new Error("No shop selected.");
    
            var shop = shop_id;
    
            
            var detail = await this.orm.call('hotel.reservation', 'get_datas', [0], { shop });
            if (!detail) throw new Error("No details returned from the backend.");
    
    
            // Update the DOM elements with the returned details
            document.getElementById('check_in').innerHTML = detail.check_in || "N/A";
    
            document.getElementById('check_out').innerHTML = detail.check_out || "N/A";
    
            document.getElementById('total').innerHTML = detail.total || "N/A";
    
            document.getElementById('booked').innerHTML = detail.booked || "N/A";
    
        } catch (error) {
            console.error("Error in total_detail: ", error.message);
        }
    }

	
scheduleDataReload() {
    // Clear any existing interval to prevent multiple intervals running concurrently
    this.clearScheduledReload();

    // Set a new interval
    intervalId = setInterval(async () => {
        try {
            await this.reload(); // Reload data
            console.log('Reloading data...'); // Log message
        } catch (error) {
            console.error("Error in scheduled data reload:", error);
        }
    }, 120000);
}


clearScheduledReload() {
    if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
    }
}


    async reload(){
		this.total_detail()
	const toolbarBox = document.getElementById('toolbar_box')
	if (toolbarBox) {
        toolbarBox.style.display = 'block';
    } else {
        console.warn("Element with ID 'toolbar_box' not found.");
    }
	
		if (document.getElementById('tbl_dashboard') === null) {
			
			var table = document.createElement('table');
			table.id = 'tbl_dashboard';
			table.className = 'CSSTableGenerator';
			
			
			const bookingCalendar = document.getElementById('booking_calendar');
			console.log("bookingCalendar:=========", bookingCalendar);
			
    		// console.log("Created table element:=======", table);

			document.getElementById('booking_calendar').appendChild(table);
	
			
		}

    //    $("#tbl_dashboard").html("");
			document.getElementById('tbl_dashboard').innerHTML = '';
			var self = this;
			// $("#date_detail").html(this.date_detail);
			document.getElementById('date_detail').innerHTML = this.date_detail;
			self.next_date = new Date(self.from_date);
			var current_date = new Date()
			// var current_date_format = `${current_date.getFullYear()}-${(current_date.getMonth() + 1).toString().padStart(2, "0")}-${current_date.getDate().toString().padStart(2, "0")}`
			var current_date_format = `${current_date.getFullYear()}-${(current_date.getMonth() + 1).toString().padStart(2, "0")}-${current_date.getDate().toString().padStart(2, "0")}`;
			console.log(current_date_format);
			var th = '<th width="100px" height="27px" t-att-data-id="Room Type" class="fc-cell-room">Room Type</th>';
			var td;
			var tdmonths = '<td  width="200px" ><div class="extra_div"></div></td>';

			if (self.from_date > self.to_date) {
				alert("To Date must be greater than From Date");
				return true;
			}
					//*****************Creating Table headers**********************************
					var cnt = 0;
					while (self.next_date <= self.to_date) {
						var year = self.next_date.getFullYear();
						var month = (self.next_date.getMonth() + 1).toString().padStart(2, "0"); // Months are 0-based, so add 1
						var day = self.next_date.getDate().toString().padStart(2, "0");

						var next_date_format = year + '-' + month + '-' + day;

						var prev_date = new Date(self.next_date);
						var dayOfWeek = self.next_date.getDay();

						prev_date.setDate(prev_date.getDate() - 1);
						if(next_date_format == current_date_format){
							  th += '<th style="background-color:#5ad4e4;" class="current-day">' + self.next_date.toDateString().substr(0, 3) + "<br/>" + self.next_date.getDate() + "</th>";
						}

						else if (dayOfWeek === 0 || dayOfWeek === 6) {
							 th += '<th style="background-color:#f8fabe;" class="weekend-day">' + self.next_date.toDateString().substr(0, 3) + "<br/>" + self.next_date.getDate() + "</th>";
						} 
                        
                    
						else{
							 th += '<th class="fc-cell-content1">' + self.next_date.toDateString().substr(0, 3) + "<br/>" + self.next_date.getDate() + "</th>";
							tdmonths = tdmonths + "<td></td>";}

					    

					
						self.next_date.setDate(self.next_date.getDate() + 1);
						cnt++;
						
					}
					
					
					var table = document.getElementById('tbl_dashboard');
					// Create a new <tr> element
					var row = document.createElement('tr');

					// Set the inner HTML of the new <tr> element to 'th'
					row.innerHTML = th;

					// Append the new <tr> element to the table
					table.appendChild(row);
					var shop_id = document.getElementById("shops").value;
					

					if (shop_id){
						self.next_date.setDate(self.next_date.getDate() - cnt);
						var roomtype = await this.orm.call('hotel.room_type', 'list_room_type', [0], {shop_id})

						
						for(var i=0;i<roomtype.length;i++){
							
							var roomtypes ='<td class="fc-cell-rooms" clicked="false" t-att-data-id='+roomtype[i].name+'>' + roomtype[i].name +'  '+'<span class="fa fa-sort-asc"></span></td>'
							
							
							var table = document.getElementById('tbl_dashboard');

							// Create a new row element
							var newRow = document.createElement('tr');

							// Set the inner HTML of the new row
							newRow.innerHTML = roomtypes;

							// Append the new row to the table
							table.appendChild(newRow);





							
							
							var res = roomtype[i].id
							var room = await this.orm.call('hotel.room_type', 'list_room', [0], {res,shop_id})
							
							for(var j=0;j<room.length;j++){
								var tss = ''
								var room_id = room[j].id
								var cater_id = roomtype[i].id
								// var shop_id = $('#shops').val()
								var shopsElement = document.getElementById('shops');
								// Get the value of the selected element
								var shop_id = shopsElement.value;

								var result = await this.orm.call('hotel.reservation', 'search_reserve_room', [0], {room_id,cater_id,shop_id})
								var dates = []

								var hotelroom = result.reservations
								for (var h=0;h<hotelroom.length; h++){
									var checkin = hotelroom[h].checkin
									var ref_no = hotelroom[h].ref_no
									checkin = checkin.split(" ")[0]
									var status = hotelroom[h].status
									var chkout = hotelroom[h].checkout
									chkout = chkout.split(' ')[0]
									var id = hotelroom[h].id
									
									var customer_name = hotelroom[h].customer_name;
									var days = {
										'checkin' : checkin,
										'checkout': chkout,
										'status':status,
										'ref_no':ref_no,
										'id':id,
										'customer_name':customer_name
										//'boolean':boolean
									}
									dates.push(days)
								}
								self.next_date = new Date(self.from_date);
								var count = 0
								if (room[j].name.indexOf(' ') !== -1) {
									hotelname = room[j].name.replace(/ /g, '-');
								} else {
									hotelname = room[j].name
								}
								for(var s=0;s<=cnt-1;s++){
										var month_id = (self.next_date.getMonth()+1).toString().padStart(2, "0");
										var dayOfWeek = self.next_date.getDay();
										var td_class = (dayOfWeek === 0 || dayOfWeek === 6) ? 'weekend-day' : 'fc-cell-content';
										var cellId = hotelname + '_' + self.next_date.getFullYear() + '-' + month_id + '-' + self.next_date.getDate().toString().padStart(2, "0");
										tss += '<td id="' + cellId + '" class="' + td_class + '" data-id=' + room[j].id + ' ' + 'room_type=' + roomtype[i].id + '></td>';
						
										// tss += '<td id="' + hotelname + '_' + self.next_date.getFullYear() + '-' + month_id + '-' + self.next_date.getDate().toString().padStart(2, "0") + '" class="' + td_class + '" data-id=' + room[j].id + ' ' + 'room_type=' + roomtype[i].id + '></td>';
										// console.log('Created cell:', cellId, 'Class:', td_class, 'Data ID:', room[j].id, 'Room Type:', roomtype[i].id);
										self.next_date.setDate(self.next_date.getDate() + 1);
										
								}
								var roomtd = '<td class="fc-cell-roomname" room_type='+roomtype[i].id+' t-att-data-id='+room[j].name+'>' + room[j].name + tss + '</td>'
								// $("#tbl_dashboard").append("<tr class='"+roomtype[i].name+"'>" + roomtd + "</tr>")

								// Create a new <tr> element
								var row = document.createElement('tr');

								// Set the class of the <tr> element
								row.className = roomtype[i].name;

								// Set the inner HTML of the <tr> element
								row.innerHTML = roomtd;

								// Select the table element with id 'tbl_dashboard'
								var table = document.getElementById('tbl_dashboard');

								// Append the new <tr> element to the table
								table.appendChild(row);

								

								for (var d=0; d<dates.length; d++){

									if (dates.length !=0){
										if(dates[d]['status'] == 'draft'  ){

										var checkin_date = new Date(dates[d]['checkin'])
										var checkout_date = new Date(dates[d]['checkout'])
										var ckn = document.getElementById(hotelname + '_' + dates[d]['checkin']);
										if (ckn) {
    ckn.innerHTML = `<div class="parent-container">
                         <span class="td-center-text">${dates[d]['ref_no']} ${dates[d]['customer_name']}</span>
                     </div>`;
}
										var day_count = 1;
										while(checkin_date <= checkout_date){
										var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;
													console.log("Formatted Check-in Date:", str_checkin_date);
													var chin = document.getElementById(hotelname + '_' + str_checkin_date);
													if(chin){
													chin.classList.remove('fc-cell-content');
													if(day_count == 1){

														chin.classList.add('half-right-draft', 'reserved')
														console.log("11111111111111111111111111111",dates)
														chin.setAttribute('data-id', dates[d]['id']);
													}else if(checkin_date.getDate() == checkout_date.getDate()){
														chin.classList.add('fc-cell-content', 'half-left-draft')
													}else{
														chin.style.backgroundColor = '#a1cef7';
														chin.classList.add('reserved')
														chin.setAttribute('data-id',dates[d]['id'])
													}
													// chin.style.display = 'flex';
													// chin.style.maxWidth = '40px';
													// chin.style.overflow = 'unset';
													
													checkin_date.setDate(checkin_date.getDate()+1)
													day_count=day_count+1;	
												}
												
												else {
													checkin_date.setDate(checkin_date.getDate()+1)
													
											}
												}
										}
										





									if(dates[d]['status'] == 'confirm'){
										var checkin_date = new Date(dates[d]['checkin'])
										var checkout_date = new Date(dates[d]['checkout'])
										// var ckn = $('#'+hotelname+'_'+dates[d]['checkin'])

										// Construct the ID from the existing variables
										var checkinId = hotelname + '_' + dates[d]['checkin']; // Adjust the index [0] if necessary

										// Use plain JavaScript to get the element by ID
										var ckn = document.getElementById(checkinId);
										if (ckn) {
    ckn.innerHTML = "<div class='parent-container'><span class='td-center-text'>" + dates[d]['ref_no'] + " " + dates[d]['customer_name'] + "</span></div>";
}
										var day_count_confirm = 1;
										while(checkin_date <= checkout_date){
                                            
											var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;                                                
											var chin = document.getElementById(hotelname + '_' + str_checkin_date);
											// Set 'data-id' attribute to the current reservation ID
												
											// Remove the 'fc-cell-content' class
											if(chin){
											chin.classList.remove('fc-cell-content');
											if(day_count_confirm == 1){
                                                chin.classList.add('half-right-confirm','reserved')
                                                chin.setAttribute('data-id',dates[d]['id'])
                                            }else if(checkin_date.getDate() == checkout_date.getDate()){
                                                chin.classList.add('fc-cell-content','half-left-confirm')
                                            }else{
                                                chin.style.backgroundColor = '#33acf2';
                                                chin.classList.add('reserved')
                                                chin.setAttribute('data-id',dates[d]['id'])
                                            }

											// chin.style.display = 'flex';
											// chin.style.maxWidth = '40px';
											// chin.style.overflow = 'unset';
											checkin_date.setDate(checkin_date.getDate()+1)
											day_count_confirm=day_count_confirm+1;
										}

										else {
													checkin_date.setDate(checkin_date.getDate()+1)
													
											}

											}
											

										}
									}
									
								}


							}
						
						}

						var shop_id = document.getElementById("shops").value

						var folio_detail = await this.orm.call('hotel.reservation', 'search_folio', [0], {shop_id})

						for (var f=0;f<folio_detail.length;f++){

								var checkin = folio_detail[f].checkin
								checkin = checkin.split(" ")[0]
								console.log("bbbbbbbbbbbbbbbbbbbbbbbb",folio_detail[f].status,folio_detail[f])
								var status = folio_detail[f].status
								var chkout = folio_detail[f].checkout
								chkout = chkout.split(' ')[0]
								if (folio_detail[f].room_name.indexOf(' ') !== -1) {
									froomname = folio_detail[f].room_name.replace(/ /g, '-');
								} else {
									froomname = folio_detail[f].room_name
								}
								if(status != 'check_out' && status != 'done' && status != 'cancel'){
								var checkin_date = new Date(checkin)
								var checkout_date = new Date(chkout)
                                var ckn = document.getElementById(froomname + '_' + checkin);

								if (ckn) {
    ckn.innerHTML = "<div class='parent-container'><span class='td-center-text'>" + folio_detail[f].fol_no + " " + folio_detail[f].customer_name + "</span></div>";
}
								var day_count_checkin = 1
								while(checkin_date <= checkout_date){
									var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;
            						var chin = document.getElementById(froomname + '_' + str_checkin_date);

									// Remove class 'fc-cell-content'
									if(chin){
									    chin.classList.remove('fc-cell-content');
                                        if(day_count_checkin == 1){
                                            chin.classList.add('half-right-checkin','folio')
                                            chin.setAttribute('data-id',folio_detail[f].id)
                                        }else if(checkin_date.getDate() == checkout_date.getDate()){
                                            chin.classList.add('fc-cell-content','half-left-checkin')
                                        }else{
                                            chin.style.backgroundColor = '#3ef78d'
                                            chin.classList.add('folio')
                                            chin.setAttribute('data-id',folio_detail[f].id)
                                        }

                                        // chin.style.display = 'flex';
                                        // chin.style.maxWidth = '40px';
                                        // chin.style.overflow = 'unset';
                                        checkin_date.setDate(checkin_date.getDate()+1)
                                        day_count_checkin = day_count_checkin + 1;
									}
									else{
                                        checkin_date.setDate(checkin_date.getDate()+1)
                                    }
								}

								}
								if(status == 'check_out' || status == 'done'){
									var checkin_date = new Date(checkin)
									var checkout_date = new Date(chkout)
									var ckn = document.getElementById(froomname + '_' + checkin);

									// ckn.text(folio_detail[f].fol_no + ' ' + folio_detail[f].customer_name)
									if (ckn) {
    ckn.innerHTML = "<div class='parent-container'><span class='td-center-text'>" + folio_detail[f].fol_no + " " + folio_detail[f].customer_name + "</span></div>";
}
									var day_count_checkout = 1;
									while(checkin_date <= checkout_date){
										var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;
            							var chin = document.getElementById(froomname + '_' + str_checkin_date);
										if(chin){
                                            chin.classList.remove('fc-cell-content'); // Replaced .removeClass()
                                            // HALF CHECKOUT color
                                            if(day_count_checkout == 1){
                                                chin.classList.add('half-right-checkout','folio')
                                                chin.setAttribute('data-id',folio_detail[f].id)
                                            }else if(checkin_date.getDate() == checkout_date.getDate()){
                                                chin.classList.add('fc-cell-content','half-left-checkout')
                                            }else{
                                                chin.style.backgroundColor = '#faaf6e'
                                                chin.classList.add('folio')
                                                chin.setAttribute('data-id',folio_detail[f].id)
                                            }

                                            // chin.style.display = 'flex';
                                            // chin.style.maxWidth = '40px';
                                            // chin.style.overflow = 'unset';
                                            checkin_date.setDate(checkin_date.getDate()+1)
                                            day_count_checkout = day_count_checkout + 1;
										}
										else{
                                            checkin_date.setDate(checkin_date.getDate()+1)
                                        }
									}
									}

						}
						var shop_id = document.getElementById('shops').value; // Replaced jQuery .val()
						var cleaning_detail = await this.orm.call('hotel.reservation', 'search_cleaning', [0], {shop_id});
						for (var g=0;g<cleaning_detail.length;g++){
							var checkin = cleaning_detail[g].checkin
							checkin = checkin.split(" ")[0]
							var status = cleaning_detail[g].status
							var chkout = cleaning_detail[g].checkout
							chkout = chkout.split(' ')[0]
							if (cleaning_detail[g].room_no.indexOf(' ') !== -1) {
								croomname = cleaning_detail[g].room_no.replace(/ /g, '-');
							} else {
								croomname = cleaning_detail[g].room_no
							}
							if(status != 'done'){
							var checkin_date = new Date(checkin)
							var checkout_date = new Date(chkout)
							var ckn = document.getElementById(croomname + '_' + checkin); // Replaced jQuery selector
								// ckn.text('Unavilable')
							if (ckn) {
    ckn.innerHTML = "<div class='parent-container'><span class='td-center-text'>Unavilable</span></div>";
}// Replaced .text()
								var day_count_clean = 1;
							while(checkin_date <= checkout_date){
								var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;
								var chin = document.getElementById(croomname + '_' + str_checkin_date); // Replaced jQuery selector
								if(chin){
                                    chin.classList.remove('fc-cell-content'); // Replaced .removeClass()
                                    chin.style.overflow = 'hidden'; // Replaced .css('overflow', ...)
                                    if(day_count_clean == 1){
                                        chin.classList.add('half-right-clean','cleaning')
                                        chin.setAttribute('data-id',cleaning_detail[g].id)
                                    }else if(checkin_date.getDate() == checkout_date.getDate()){
                                        chin.classList.add('fc-cell-content','half-left-clean')
                                    }else{
                                        chin.style.backgroundColor = '#95a5a6';
                                        chin.classList.add('cleaning')
                                        chin.setAttribute('data-id',cleaning_detail[g].id)
                                    }
                                    checkin_date.setDate(checkin_date.getDate()+1)
                                    day_count_clean = day_count_clean + 1;
								}
								else{
                                    checkin_date.setDate(checkin_date.getDate()+1)
                                }
							}
							}
						}
						var shop_id = document.getElementById('shops').value; // Replaced jQuery .val()
						var repair_detail = await this.orm.call('hotel.reservation', 'search_repair', [0], {shop_id});
						for (var l=0;l<repair_detail.length;l++){
							var date = repair_detail[l].date
							dates = date.split(" ")[0]
							var status = repair_detail[l].status
							if (repair_detail[l].room_no.indexOf(' ') !== -1) {
								mroomname = repair_detail[l].room_no.replace(/ /g, '-');
							} else {
								mroomname = repair_detail[l].room_no
							}
							// var chkout = repair_detail[l].checkout
							var date2 = dates
							if(status != 'done'){
							var checkin_date = new Date(dates)
							var checkout_date = new Date(date2)
							var ckn = document.getElementById(mroomname + '_' + dates);
							if (ckn) {
    ckn.innerHTML = "<div class='parent-container'><span class='td-center-text'>Maintenance</span></div>";
}
							
							var day_count_repair = 1;
							while(checkin_date <= checkout_date){
								var str_checkin_date = `${checkin_date.getFullYear()}-${(checkin_date.getMonth() + 1).toString().padStart(2, "0")}-${checkin_date.getDate().toString().padStart(2, "0")}`;
            					var chin = document.getElementById(mroomname + '_' + str_checkin_date); // Replaced jQuery selector
								if(chin){
								    chin.classList.remove('fc-cell-content'); // Replaced .removeClass()
                                    if(day_count_repair == 1){
                                        chin.classList.add('half-right-repair','repair')
                                        chin.setAttribute('data-id',repair_detail[l].id)
                                    }else if(checkin_date.getDate() == checkout_date.getDate()){
                                        chin.classList.add('fc-cell-content','half-left-repair')
                                    }else{
                                        chin.style.backgroundColor = '#b9bdb9'
                                        chin.classList.add('repair')
                                        chin.setAttribute('data-id',repair_detail[l].id)
                                    }

                                    chin.style.overflow = 'hidden'; // Replaced .css('overflow', ...)
									chin.style.maxWidth = '40px';

                                    checkin_date.setDate(checkin_date.getDate()+1)
                                    day_count_repair = day_count_repair + 1;
								}
								else{
                                    checkin_date.setDate(checkin_date.getDate()+1)
                                }
							}
							}

						}
				}
					
				function pad(number) {
  if (number < 10) {
    return '0' + number;
  }
  return number;
}	


				
document.querySelectorAll('.fc-cell-content').forEach(function(element) {
    element.addEventListener('mouseup', async function(ev) {
        ev.preventDefault();
        mousedown = false;

        // Clear previous selection styles
        selection.forEach(function(sel) {
            var selectedElement = document.getElementById(sel);
            if (selectedElement) {
                selectedElement.style.backgroundColor = '';
                selectedElement.style.outline = 'none';
            }
        });

        // Get checkout, room, and room type information
        var checkout = this.id.split('_')[1];
        var room = this.getAttribute('data-id');
        var room_type = this.getAttribute('room_type');

        // Error handling for missing room or room_type
        if (!room || !room_type) {
            window.alert("Room or Room Type is missing. Please try again.");
            return;  // Exit if room or room_type is not provided
        }

        // Handle selected days and checkin date
        selected_days.push(checkout);
        var checkin = selected_days[0];

        // Dates initialization
        var startdatenew = new Date(checkin);
        var startdatecheckin = new Date(checkin);

        // Call to Odoo to get reservation details
        try {
            var details = await self.orm.call('hotel.reservation', 'create_detail', [0], { room, room_type, checkout, checkin });
        } catch (error) {
            console.error("Error fetching reservation details:", error);
            window.alert("Failed to retrieve reservation details. Please try again.");
            return;  // Exit if there's an error fetching reservation details
        }

        var shop_id = document.getElementById('shops').value;
        var startdate = new Date(selected_days[0]);
        var enddate = new Date(selected_days[1]);
		var newDate = details[0].checkout
		var newDate = new Date(newDate)
		var checkoutdate_time = new Date(newDate)
		var user_timezone_offset = details[0].user_hour_min
		var timeString = user_timezone_offset;

		// Parse the time string
		var timeParts = timeString.split(':');
		var hours = parseInt(timeParts[0]);
		var minutes = parseInt(timeParts[1]);
		var seconds = parseInt(timeParts[2]);
			startdatecheckin.setHours(hours);
			startdatecheckin.setMinutes(minutes);
			startdatecheckin.setSeconds(seconds);

			checkoutdate_time.setHours(hours);
			checkoutdate_time.setMinutes(minutes);
			checkoutdate_time.setSeconds(seconds);
	   

			 startdatecheckin.setHours(startdatecheckin.getHours() - 5);
			 startdatecheckin.setMinutes(startdatecheckin.getMinutes() - 30);

			 checkoutdate_time.setHours(checkoutdate_time.getHours() - 5);
			 checkoutdate_time.setMinutes(checkoutdate_time.getMinutes() - 30);

			   const formattedDate =
				  startdatecheckin.getFullYear() +
					"-" +
					pad(startdatecheckin.getMonth() + 1) +
					"-" +
					pad(startdatecheckin.getDate()) +
					" " +
					pad(startdatecheckin.getHours()) +
					":" +
					pad(startdatecheckin.getMinutes()) +
					":" +
					pad(startdatecheckin.getSeconds());


					var formattedDatecheckout =

					checkoutdate_time.getFullYear() +
					"-" +
					pad(checkoutdate_time.getMonth() + 1) +
					"-" +
					pad(checkoutdate_time.getDate()) +
					" " +
					pad(checkoutdate_time.getHours()) +
					":" +
					pad(checkoutdate_time.getMinutes()) +
					":" +
					pad(checkoutdate_time.getSeconds());

        // Fetch checkout policy configuration
        const checkOut_policy = await self.orm.call("checkout.configuration", "hotel_checkout_policy", [[], parseInt(shop_id)]);
        if (checkOut_policy) {
					formattedDatecheckout = checkoutdate_time.getFullYear() + "-" + 
					pad(checkoutdate_time.getMonth() + 1) + "-" + 
					pad(checkoutdate_time.getDate()) + " " + 
					pad(checkOut_policy - 6) + ":" + 
					pad(30) + ":" +
					pad(0);
        }

        // Get current date and compare checkin date with today
        const currentDate = new Date();
        const yesterday = new Date(currentDate.getTime() - 1000 * 60 * 60 * 24);

        // Validate checkin and checkout dates
        if (startdate > enddate) {
            window.alert("Checkin Date must be less than Checkout Date");
        } else if (yesterday >= startdate) {
            window.alert("Checkin Date must be Equal or Greater than today");
        } else {
            // Perform action for hotel reservation
            self.actionService.doAction({
                name: _t("Hotel Reservation"),
                res_model: 'hotel.reservation',
                views: [[false, 'form']],
                view_mode: 'form',
                type: 'ir.actions.act_window',
                target: "new",
                context: {
                    'default_shop_id': Number(shop_id),
                    'default_reservation_line': [
                        {
							'checkin': formattedDate,
                            'checkout': formattedDatecheckout,
                            'categ_id': parseInt(details[0].cat_id),
                            'room_number': parseInt(details[0].room),
                            'price': parseInt(details[0].price),
                            'company_id': parseInt(shop_id),
                        },
                    ]
                },
            });
        }
    });
});




///////////////////////////////////// weekend day function//////////////////////////

const weekendDays = document.querySelectorAll('.weekend-day');

weekendDays.forEach(day => {
    day.addEventListener('mouseup', async function(ev) {
        ev.preventDefault();
        mousedown = false;

        // Clear selection styles
        selection.forEach(sel => {
            const selectedElement = document.getElementById(sel);
            if (selectedElement) {
                selectedElement.style.backgroundColor = '';
                selectedElement.style.outline = 'none';
            }
        });

        const checkout = this.id.split('_')[1] || ''; // Default to empty string
        const room = this.getAttribute('data-id') || ''; // Default to empty string
        const room_type = this.getAttribute('room_type') || ''; // Default to empty string

        if (!room || !room_type) {
            console.warn("Room or room_type is undefined. Skipping reservation creation.");
            return; // Exit if undefined
        }

        selected_days.push(checkout);
        const checkin = selected_days[0] || ''; // Default to empty string

        const startdatenew = new Date(checkin);
        const startdatecheckin = new Date(checkin);
        
        try {
            const details = await self.orm.call('hotel.reservation', 'create_detail', [0], { room, room_type, checkout, checkin });

            const shop_id = document.getElementById('shops')?.value || 0; // Default to 0 if not found
            const startdate = new Date(selected_days[0]);
            const enddate = new Date(selected_days[1]);
            const newDate = new Date(details[0]?.checkout); // Safely access checkout
            const checkoutdate_time = new Date(newDate);
            const user_timezone_offset = details[0]?.user_hour_min || '00:00:00'; // Default to '00:00:00'

            const timeParts = user_timezone_offset.split(':');
            const hours = parseInt(timeParts[0]) || 0;
            const minutes = parseInt(timeParts[1]) || 0;
            const seconds = parseInt(timeParts[2]) || 0;

            startdatecheckin.setHours(hours);
            startdatecheckin.setMinutes(minutes);
            startdatecheckin.setSeconds(seconds);
            checkoutdate_time.setHours(hours);
            checkoutdate_time.setMinutes(minutes);
            checkoutdate_time.setSeconds(seconds);

            // Adjust time for timezone (if needed)
            startdatecheckin.setHours(startdatecheckin.getHours() - 5);
            startdatecheckin.setMinutes(startdatecheckin.getMinutes() - 30);
            checkoutdate_time.setHours(checkoutdate_time.getHours() - 5);
            checkoutdate_time.setMinutes(checkoutdate_time.getMinutes() - 30);

            const formattedDate = `${startdatecheckin.getFullYear()}-${pad(startdatecheckin.getMonth() + 1)}-${pad(startdatecheckin.getDate())} ${pad(startdatecheckin.getHours())}:${pad(startdatecheckin.getMinutes())}:${pad(startdatecheckin.getSeconds())}`;
            let formattedDatecheckout = `${checkoutdate_time.getFullYear()}-${pad(checkoutdate_time.getMonth() + 1)}-${pad(checkoutdate_time.getDate())} ${pad(checkoutdate_time.getHours())}:${pad(checkoutdate_time.getMinutes())}:${pad(checkoutdate_time.getSeconds())}`;

            const checkOut_policy = await self.orm.call("checkout.configuration", "hotel_checkout_policy", [[], parseInt(shop_id)]);

            if (checkOut_policy) {
                formattedDatecheckout = `${checkoutdate_time.getFullYear()}-${pad(checkoutdate_time.getMonth() + 1)}-${pad(checkoutdate_time.getDate())} ${pad(checkOut_policy - 6)}:${pad(30)}:${pad(0)}`;
            }

            const currentdate = new Date();
            const yesterday = new Date(currentdate.getTime() - 1000 * 60 * 60 * 24);

            if (startdate > enddate) {
                window.alert("Checkin Date must be less than Checkout Date");
            } else if (yesterday >= startdate) {
                window.alert("Checkin Date must be Equal or Greater than today");
            } else {
                self.actionService.doAction({
                    name: _t("Hotel Reservation"),
                    res_model: 'hotel.reservation',
                    views: [[false, 'form']],
                    view_mode: 'form',
                    type: 'ir.actions.act_window',
                    target: "new",
                    context: {
                        'default_shop_id': Number(shop_id),
                        'default_reservation_line': [
                            {
                                'checkin': formattedDate,
                                'checkout': formattedDatecheckout,
                                'categ_id': parseInt(details[0]?.cat_id) || 0,
                                'room_number': parseInt(details[0]?.room) || 0,
                                'price': parseInt(details[0]?.price) || 0,
                                'company_id': parseInt(shop_id) || 0,
                            },
                        ]
                    },
                });
                // self.reload();
            }
        } catch (error) {
            console.error("An error occurred while creating the reservation:", error);
            // Optionally, provide feedback to the user here
        }
        // self.reload();
    });
});




////////////////////////// weekend mouse down function///////////////

	const weekenddaysmousedown = document.querySelectorAll('.weekend-day');
	weekenddaysmousedown.forEach(function(day) {
		day.addEventListener('mouseover', function() {
			if (mousedown) {
				// Set styles for the previously selected element
				const selectedElement = document.getElementById(selection[0]);
				if (selectedElement) {
					selectedElement.style.backgroundColor = '#fffa91';
					selectedElement.style.outline = '1px solid #ccc';
				}

				// Set styles for the current element
				this.style.backgroundColor = '#ffc04c';
				this.style.outline = '1px solid #ccc';
				selection.push(this.id);
			}
		});
	});

///////////////////////////////weekend mouseover function//////////////////

	const weekenddaysmouseover = document.querySelectorAll('.weekend-day');

	weekenddaysmouseover.forEach(function(day) {
		day.addEventListener('mouseover', function() {
			if (mousedown) {
				// Set styles for the previously selected element
				const selectedElement = document.getElementById(selection[0]);
				if (selectedElement) {
					selectedElement.style.backgroundColor = '#fffa91';
					selectedElement.style.outline = '1px solid #ccc';
				}

				// Set styles for the current element
				this.style.backgroundColor = '#ffc04c';
				this.style.outline = '1px solid #ccc';

				// Add the current element's ID to the selection array
				selection.push(this.id);
			}
		});
	});



	const reservedElements = document.querySelectorAll('.reserved');

	reservedElements.forEach(function(element) {
		element.addEventListener('mousedown', async function(ev) {
			ev.preventDefault();

			// Get the view ID
			var view_id = await self.orm.call('hotel.reservation', 'get_view_reserve', [0], {});
			
			var checkin = this.id.split('_')[1];
			var id = this.getAttribute('data-id');

			if (id) {
				self.actionService.doAction({
					name: _t("Hotel Reservation"),
					res_model: 'hotel.reservation',
					res_id: parseInt(id),
					views: [[view_id, 'form']],
					view_mode: 'form',
					type: 'ir.actions.act_window',
					target: "new",
					context: {},
				});
				// Optionally reload
				// self.reload();
			}
		});
	});

	const folioElements = document.querySelectorAll('.folio');

	folioElements.forEach(function(element) {
		element.addEventListener('mousedown', function(ev) {
			ev.preventDefault();
			
			var checkin = this.id.split('_')[1];
			var id = this.getAttribute('data-id');

			self.actionService.doAction({
				name: _t("Folio"),
				res_model: 'hotel.folio',
				res_id: parseInt(id),
				views: [[false, 'form']],
				view_mode: 'form',
				type: 'ir.actions.act_window',
				target: "new",
				context: {},
			});
		});
	});

	
	const cleaningElements = document.querySelectorAll('.cleaning');
	console.log("++++++++++++cleaningElements========",cleaningElements)
	cleaningElements.forEach(function(element) {
		element.addEventListener('mousedown', function(ev) {
			ev.preventDefault();
			
			var checkin = this.id.split('_')[1];
			var id = this.getAttribute('data-id');

			self.actionService.doAction({
				name: _t("Housekeeping"),
				res_model: 'hotel.housekeeping',
				res_id: parseInt(id),
				views: [[false, 'form']],
				view_mode: 'form',
				type: 'ir.actions.act_window',
				target: "new",
				context: {},
			});
		});
	});

		const repairElements = document.querySelectorAll('.repair');

		repairElements.forEach(function(element) {
			element.addEventListener('mousedown', function(ev) {
				ev.preventDefault();
				
				var date = this.id.split('_')[1];
				var id = this.getAttribute('data-id');

				self.actionService.doAction({
					name: _t("Request for Repair / Replacement"),
					res_model: 'rr.housekeeping',
					res_id: parseInt(id),
					views: [[false, 'form']],
					view_mode: 'form',
					type: 'ir.actions.act_window',
					target: "new",
					context: {},
				});
			});
		});

		const cellContentElements = document.querySelectorAll('.fc-cell-content');

		cellContentElements.forEach(function(element) {
			element.addEventListener('mousedown', function(ev) {
				mousedown = true;
				selection.length = 0;
				selected_days.length = 0;
				ev.preventDefault();

				var checkin = this.id.split('_')[1];
				selected_days.push(checkin);
				selection.push(this.id);
			});
		});
		const cellContentElementsmouseover = document.querySelectorAll('.fc-cell-content');

		cellContentElementsmouseover.forEach(function(element) {
		element.addEventListener('mouseover', function() {
			if (mousedown) {
				const selectedElement = document.getElementById(selection[0]);
				if (selectedElement) {
					selectedElement.style.backgroundColor = '#eee';
					selectedElement.style.outline = '1px solid #ccc';
				}
				this.style.backgroundColor = '#eee';
				this.style.outline = '1px solid #ccc';
				selection.push(this.id);
			}
		});
		});

const reservedElementsmouseover = document.querySelectorAll('.reserved');

reservedElementsmouseover.forEach(function (element) {
    element.addEventListener('mouseover', async function () {
        const id = this.getAttribute('data-id');
        const reserve = await self.orm.call('hotel.reservation', 'reserve_room', [0], { id });

        // Function to convert UTC time to IST by adding 5 hours and 30 minutes
        function convertUTCtoIST(utcDate) {
            const date = new Date(utcDate);  // Convert string to Date object
            date.setHours(date.getHours() + 5);  // Add 5 hours
            date.setMinutes(date.getMinutes() + 30);  // Add 30 minutes
            return date.toLocaleString();  // Return as a string in local format
        }

        // Convert UTC times to IST
        const checkinIST = convertUTCtoIST(reserve[0].checkin);
        const checkoutIST = convertUTCtoIST(reserve[0].checkout);
        console.log('CHECK IN:', checkinIST);
        console.log('CHECK OUT:', checkoutIST);

        this.setAttribute('data-toggle', 'tooltip');
        console.log('CHECK OUT: 5555555555555555555555555555');
        this.setAttribute('data-placement', 'top');
        console.log('CHECK OUT: 66666666666666666666666',reserve);
        this.setAttribute('title', `Reservation No: ${reserve[0].res_no}\nCustomer: ${reserve[0].partner}\nCheckin: ${reserve[0].checkin}\nCheckout: ${reserve[0].checkout}\nReservation Status: ${reserve[0].state}`);
        console.log('CHECK OUT: 77777777777777777777777');
        // Optionally, initialize the tooltip here if using a library
        // $(this).tooltip(); // If you have a tooltip library to initialize
    });
});



	const folioElementsmouseover = document.querySelectorAll('.folio');

	folioElementsmouseover.forEach(function(element) {
		element.addEventListener('mouseover', async function() {
			const id = this.getAttribute('data-id');
			const folio = await self.orm.call('hotel.reservation', 'folio_detail', [0], { id });
	
			this.setAttribute('data-toggle', 'tooltip');
			this.setAttribute('data-placement', 'top');
			this.setAttribute('title', `Reservation No: ${folio[0].res_no}\nCustomer: ${folio[0].partner}\nCheckin: ${folio[0].checkin}\nCheckout: ${folio[0].checkout}\nFolio Status: ${folio[0].state}`);
			
			// Optionally, initialize the tooltip if you're using a library
			// $(this).tooltip(); // If you have a tooltip library to initialize
		});
	});
	const cleaningElementsmouseover = document.querySelectorAll('.cleaning');

	cleaningElementsmouseover.forEach(function(element) {
		element.addEventListener('mouseover', async function() {
			console.log("99999999999999999999999999")
			const id = this.getAttribute('data-id');
			console.log("888888888888888888888888888888888",id)
			const clean = await self.orm.call('hotel.reservation', 'cleaning_detail', [0], { id });
	
			this.setAttribute('data-toggle', 'tooltip');
			this.setAttribute('data-placement', 'top');
			this.setAttribute('title', `Name: ${clean[0].name}\nStart date: ${clean[0].start}\nEnd date: ${clean[0].end}\nInspector: ${clean[0].inspector}\nStatus: ${clean[0].state}`);
	
			// Optionally, initialize the tooltip if you're using a library
			// $(this).tooltip(); // If you have a tooltip library to initialize
		});
	});
	const repairElementsmouseover= document.querySelectorAll('.repair');

	repairElementsmouseover.forEach(function(element) {
		element.addEventListener('mouseover', async function() {
			const id = this.getAttribute('data-id');
			const replace = await self.orm.call('hotel.reservation', 'repair_repace_detail', [0], { id });
	
			this.setAttribute('data-toggle', 'tooltip');
			this.setAttribute('data-placement', 'top');
			this.setAttribute('title', `Name: ${replace[0].name}\nOrdered date: ${replace[0].date}\nActivity: ${replace[0].activity}\nRequested By: ${replace[0].request}\nApproved By: ${replace[0].approved}\nStatus: ${replace[0].state}`);
			
			// Optionally, initialize the tooltip if you're using a library
			// $(this).tooltip(); // Uncomment if necessary
		});
	});

	const roomCells = document.querySelectorAll('.fc-cell-rooms');

	roomCells.forEach(function(cell) {
		cell.addEventListener('click', function() {
			const type = this.getAttribute('t-att-data-id');
			const clicked = this.getAttribute('clicked');
	
			if (clicked === 'false') {
				const elementsToHide = document.querySelectorAll(`.${type}`);
				elementsToHide.forEach(function(el) {
					el.style.display = 'none';
				});
				const icon = this.querySelector('i'); // Assuming the child is an <i> element for the icon
				if (icon) {
					icon.classList.remove(...icon.classList);
					icon.classList.add('fa', 'fa-sort-desc');
				}
				this.setAttribute('clicked', 'true');
			} else {
				const elementsToShow = document.querySelectorAll(`.${type}`);
				elementsToShow.forEach(function(el) {
					el.removeAttribute('style');
				});
				const icon = this.querySelector('i'); // Assuming the child is an <i> element for the icon
				if (icon) {
					icon.classList.remove(...icon.classList);
					icon.classList.add('fa', 'fa-sort-asc');
				}
				this.setAttribute('clicked', 'false');
			}
		});
	});
	

	  
    }

	async week_function(){
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const day = today.getDay();
		const daysToSubtract = day === 0 ? 6 : day - 1;
		const startDate = new Date(today.getTime() - daysToSubtract * 24 * 60 * 60 * 1000);
		const endDate = new Date(startDate.getTime() + 6 * 24 * 60 * 60 * 1000);
		const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
											"Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
										];

		const days = startDate.getDate();
		const month = monthNames[startDate.getMonth()];
		const year = startDate.getFullYear();
		const endday = endDate.getDate();
		const endmonth = monthNames[endDate.getMonth()];
		const endyear = endDate.getFullYear();
		this.date_detail =`${days} ${month} ${year} - ${endday} ${endmonth} ${endyear}`
		this.from_date = startDate
		this.to_date = endDate
		this.view_type = 'week'
		this.reload();
	}

	async month_function(){
		const today = new Date();
		today.setDate(1);
	  	today.setHours(0, 0, 0, 0);
	  	const month = today.getMonth();
		const endDate = new Date(today.getFullYear(), month + 1, 0);
		const year = today.getFullYear();
		const startDate = `${year}-${month + 1}-01`;
		const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    	this.date_detail = monthNames[month];
		// $('#date_detail').val(nextMonthName)
		// console.log('0000000000000000000000000000000',$('#date_detail').val())
		this.from_date = startDate
		this.to_date = endDate
		this.view_type = 'month'
		this.reload();
	}

	async preview_function(){
		if (this.view_type == 'week'){
			const startDate = new Date(this.from_date);
  			const endDate = new Date(this.to_date);
  			const daysToSubtract = 7
  			const previousStartDate = new Date(startDate.getTime() - daysToSubtract * 24 * 60 * 60 * 1000);
  			const previousEndDate = new Date(endDate.getTime() - daysToSubtract * 24 * 60 * 60 * 1000);
			  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
											"Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
										];

				const day = previousStartDate.getDate();
				const month = monthNames[previousStartDate.getMonth()];
				const year = previousStartDate.getFullYear();
				const endday = previousEndDate.getDate();
				const endmonth = monthNames[previousEndDate.getMonth()];
				const endyear = previousEndDate.getFullYear();
				this.date_detail =`${day} ${month} ${year} - ${endday} ${endmonth} ${endyear}`
			  this.from_date = previousStartDate
			  this.to_date = previousEndDate
			  this.reload()
		}else{
			const startDate = new Date(this.from_date);
  			const endDate = new Date(this.to_date);
  			const month = startDate.getMonth();
  			const year = startDate.getFullYear();
  			const previousMonth = new Date(year, month - 1, 1);
            const previousMonthEndDate = new Date(endDate.getFullYear(), endDate.getMonth(), 0);
			const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
			this.date_detail = monthNames[previousMonth.getMonth()];
			// $('#date_detail').val(nextMonthName)
			this.from_date = previousMonth
			this.to_date = previousMonthEndDate
			this.reload()
		}
	}

	async next_function(){
		if (this.view_type == 'week'){
			const startDate = new Date(this.from_date);
  			const endDate = new Date(this.to_date);
  			const daysToSubtract = 7
  			const nextStartDate = new Date(startDate.getTime() + daysToSubtract * 24 * 60 * 60 * 1000);
  			const nextEndDate = new Date(endDate.getTime() + daysToSubtract * 24 * 60 * 60 * 1000);
			  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
			  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
		  	];

				const days = nextStartDate.getDate();
				const month = monthNames[nextStartDate.getMonth()];
				const year = nextStartDate.getFullYear();
				const endday = nextEndDate.getDate();
				const endmonth = monthNames[nextEndDate.getMonth()];
				const endyear = nextEndDate.getFullYear();
				this.date_detail =`${days} ${month} ${year} - ${endday} ${endmonth} ${endyear}`
			  this.from_date = nextStartDate
			  this.to_date = nextEndDate
			  this.reload()
		}else{
			const startDate = new Date(this.from_date);
  			const endDate = new Date(this.to_date);
            const month = startDate.getMonth();
  			const year = startDate.getFullYear();
  			const nextMonth = new Date(year, month + 1, 1);
  			const nextMonthLastDay = new Date(nextMonth.getFullYear(), nextMonth.getMonth() + 1, 0);
			  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
			  const nextMonthName = monthNames[nextMonth.getMonth()];
			  this.date_detail = nextMonthName
			  this.from_date = nextMonth
			  this.to_date = nextMonthLastDay
			  this.reload()

		}
		
		
	}
	async today_function(){
		if (this.view_type == 'week'){
			this.week_function()
		}else{
			this.month_function()
		}

	}

	
	
    }






CalenderDashboard.template = 'hotel_dashboard_template'
registry.category("actions").add("HotelDashboardView_temp", CalenderDashboard)






































